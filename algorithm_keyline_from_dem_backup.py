import math
import heapq
import processing
import numpy as np

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingUtils,
    QgsRasterBandStats,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsProject
)


class KeylineFromDemAlgorithm(QgsProcessingAlgorithm):
    INPUT_DEM = "INPUT_DEM"
    INPUT_MASK = "INPUT_MASK"
    INPUT_EXCLUSION = "INPUT_EXCLUSION"

    CONTOUR_INTERVAL = "CONTOUR_INTERVAL"
    SPACING = "SPACING"
    N_OFFSETS = "N_OFFSETS"
    SMOOTH_ITERS = "SMOOTH_ITERS"

    MIN_LENGTH = "MIN_LENGTH"
    MAX_LENGTH = "MAX_LENGTH"
    MAX_SLOPE = "MAX_SLOPE"
    MIN_RADIUS = "MIN_RADIUS"

    DENSIFY = "DENSIFY"
    EXCLUSION_BUFFER = "EXCLUSION_BUFFER"

    FLOW_THRESHOLD_AREA = "FLOW_THRESHOLD_AREA"
    MAX_HYDRO_CELLS = "MAX_HYDRO_CELLS"

    OUTPUT = "OUTPUT"
    OUTPUT_POINTS = "OUTPUT_POINTS"
    OUTPUT_DRAINAGE = "OUTPUT_DRAINAGE"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def name(self):
        return "keyline_from_dem_v032"

    def displayName(self):
        return self.tr("Generar LDI/Keyline desde DEM - Fase 2.2 v0.3.2")

    def group(self):
        return self.tr("Basdonax Keyline")

    def groupId(self):
        return "basdonax_keyline"

    def shortHelpString(self):
        return self.tr(
            "Genera lineas LDI/Keyline desde DEM. "
            "Fase 2.2: D8 hibrido DEM original + epsilon-fill, diagnostico de linea madre, "
            "diagnostico de offsets, drenajes potenciales y penalizacion hidrologica."
        )

    def createInstance(self):
        return KeylineFromDemAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DEM,
                self.tr("DEM / DTM en metros")
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_MASK,
                self.tr("Mascara de area de diseno opcional"),
                [QgsProcessing.TypeVectorPolygon],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_EXCLUSION,
                self.tr("Restricciones / exclusiones opcionales"),
                [QgsProcessing.TypeVectorAnyGeometry],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.EXCLUSION_BUFFER,
                self.tr("Buffer de exclusion (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=3.0,
                minValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.CONTOUR_INTERVAL,
                self.tr("Intervalo de curvas (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.5,
                minValue=0.01
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SPACING,
                self.tr("Espaciamiento entre lineas (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=3.5,
                minValue=0.1
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.N_OFFSETS,
                self.tr("Cantidad de offsets por lado"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=100,
                minValue=1
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SMOOTH_ITERS,
                self.tr("Iteraciones de suavizado Chaikin"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2,
                minValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_LENGTH,
                self.tr("Longitud minima de linea (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=20.0,
                minValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_LENGTH,
                self.tr("Longitud maxima continua de linea (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=200.0,
                minValue=10.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_SLOPE,
                self.tr("Pendiente longitudinal maxima admisible (%)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.50,
                minValue=0.01
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_RADIUS,
                self.tr("Radio minimo admisible (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=12.0,
                minValue=1.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.DENSIFY,
                self.tr("Densificacion para muestreo DEM / GNSS (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.0,
                minValue=0.2
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.FLOW_THRESHOLD_AREA,
                self.tr("Umbral de area contribuyente para drenaje potencial (m2)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=500.0,
                minValue=1.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_HYDRO_CELLS,
                self.tr("Maximo de celdas para hidrologia en memoria"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2000000,
                minValue=10000
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Lineas LDI / Keyline"),
                type=QgsProcessing.TypeVectorLine
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POINTS,
                self.tr("Puntos GNSS / replanteo"),
                type=QgsProcessing.TypeVectorPoint
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_DRAINAGE,
                self.tr("Drenajes potenciales derivados del DEM"),
                type=QgsProcessing.TypeVectorLine
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        dem = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)

        if dem is None:
            raise QgsProcessingException("DEM invalido.")

        dem_crs = dem.crs()

        if not dem_crs.isValid():
            raise QgsProcessingException("El DEM no tiene CRS valido.")

        if dem_crs.mapUnits() != Qgis.DistanceUnit.Meters:
            raise QgsProcessingException(
                "El CRS del DEM no esta en metros. Reproyecte a un CRS proyectado metrico."
            )

        if dem_crs.authid() != "EPSG:8908":
            feedback.pushWarning(
                f"CRS detectado: {dem_crs.authid()}. "
                "Para Costa Rica se recomienda EPSG:8908 / CRTM05 vigente. "
                "Si el proyecto no es de Costa Rica, basta con que el CRS este en metros."
            )

        mask_layer = self.parameterAsVectorLayer(parameters, self.INPUT_MASK, context)
        exclusion_layer = self.parameterAsVectorLayer(parameters, self.INPUT_EXCLUSION, context)

        contour_interval = self.parameterAsDouble(parameters, self.CONTOUR_INTERVAL, context)
        spacing = self.parameterAsDouble(parameters, self.SPACING, context)
        n_offsets = self.parameterAsInt(parameters, self.N_OFFSETS, context)
        smooth_iters = self.parameterAsInt(parameters, self.SMOOTH_ITERS, context)

        min_length = self.parameterAsDouble(parameters, self.MIN_LENGTH, context)
        max_length = self.parameterAsDouble(parameters, self.MAX_LENGTH, context)
        max_slope = self.parameterAsDouble(parameters, self.MAX_SLOPE, context)
        min_radius = self.parameterAsDouble(parameters, self.MIN_RADIUS, context)

        densify = self.parameterAsDouble(parameters, self.DENSIFY, context)
        exclusion_buffer = self.parameterAsDouble(parameters, self.EXCLUSION_BUFFER, context)

        flow_threshold_area = self.parameterAsDouble(parameters, self.FLOW_THRESHOLD_AREA, context)
        max_hydro_cells = self.parameterAsInt(parameters, self.MAX_HYDRO_CELLS, context)

        self._validate_dem_basic(
            dem=dem,
            spacing=spacing,
            densify=densify,
            feedback=feedback
        )

        design_mask = self._build_mask_geometry(
            dem_layer=dem,
            mask_layer=mask_layer
        )

        if design_mask is None or design_mask.isEmpty():
            raise QgsProcessingException("No se pudo construir la mascara de diseno.")

        if not design_mask.isGeosValid():
            design_mask = design_mask.makeValid()

        exclusion_geom = self._build_exclusion_geometry(
            dem_layer=dem,
            exclusion_layer=exclusion_layer,
            buffer_m=exclusion_buffer,
            feedback=feedback
        )

        if exclusion_geom is not None and not exclusion_geom.isEmpty():
            valid_mask = design_mask.difference(exclusion_geom)

            if valid_mask is not None and not valid_mask.isEmpty():
                if not valid_mask.isGeosValid():
                    valid_mask = valid_mask.makeValid()

            feedback.pushInfo("Se aplicaron restricciones / exclusiones al area de diseno.")
        else:
            valid_mask = QgsGeometry(design_mask)

        if valid_mask is None or valid_mask.isEmpty():
            raise QgsProcessingException(
                "El area valida quedo vacia despues de aplicar restricciones."
            )

        feedback.pushInfo("Construyendo modelo hidrologico D8 basico...")

        hydro = self._build_hydrology_model(
            dem_layer=dem,
            flow_threshold_area=flow_threshold_area,
            max_cells=max_hydro_cells,
            feedback=feedback
        )

        contour = self._create_contours_layer(
            dem=dem,
            interval=contour_interval,
            context=context,
            feedback=feedback
        )

        if contour is None or not contour.isValid():
            raise QgsProcessingException("No se pudo generar o cargar la capa de contornos.")

        z_mid = self._estimate_mid_elevation_from_contours(
            contour_layer=contour,
            mask_geom=valid_mask,
            fallback_dem=dem,
            feedback=feedback
        )

        mother = self._select_mother_line(
            contour_layer=contour,
            mask_geom=valid_mask,
            z_mid=z_mid,
            dem=dem,
            densify=densify,
            min_radius=min_radius,
            max_slope=max_slope,
            hydro=hydro,
            flow_threshold_area=flow_threshold_area,
            min_length=min_length,
            feedback=feedback
        )

        if mother is None or mother.isEmpty():
            raise QgsProcessingException(
                "No se pudo seleccionar linea madre. "
                "Pruebe con menor intervalo de curvas o revise el DEM/mascara."
            )

        mother = self._chaikin_geometry(
            geom=mother,
            iterations=smooth_iters
        )

        if mother is None or mother.isEmpty():
            raise QgsProcessingException("La linea madre quedo vacia despues del suavizado.")

        fields = QgsFields()
        fields.append(QgsField("line_id", QVariant.Int))
        fields.append(QgsField("offset_m", QVariant.Double, len=12, prec=3))
        fields.append(QgsField("length_m", QVariant.Double, len=14, prec=2))

        fields.append(QgsField("z_ini", QVariant.Double, len=12, prec=3))
        fields.append(QgsField("z_fin", QVariant.Double, len=12, prec=3))
        fields.append(QgsField("z_min", QVariant.Double, len=12, prec=3))
        fields.append(QgsField("z_max", QVariant.Double, len=12, prec=3))
        fields.append(QgsField("dz_total", QVariant.Double, len=12, prec=3))

        fields.append(QgsField("slope_avg", QVariant.Double, len=10, prec=3))
        fields.append(QgsField("slope_max", QVariant.Double, len=10, prec=3))
        fields.append(QgsField("crit_len_m", QVariant.Double, len=12, prec=2))
        fields.append(QgsField("crit_len_pct", QVariant.Double, len=8, prec=2))

        fields.append(QgsField("radius_min", QVariant.Double, len=12, prec=2))

        fields.append(QgsField("facc_max", QVariant.Double, len=14, prec=2))
        fields.append(QgsField("facc_mean", QVariant.Double, len=14, prec=2))
        fields.append(QgsField("drain_hits", QVariant.Int))
        fields.append(QgsField("hyd_cls", QVariant.String, len=4))

        fields.append(QgsField("risk_cls", QVariant.String, len=6))
        fields.append(QgsField("icl", QVariant.Double, len=8, prec=2))
        fields.append(QgsField("status", QVariant.String, len=20))
        fields.append(QgsField("review", QVariant.String, len=160))

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.LineString,
            dem.crs()
        )

        if sink is None:
            raise QgsProcessingException("No se pudo crear la salida de lineas.")

        pt_fields = QgsFields()
        pt_fields.append(QgsField("line_id", QVariant.Int))
        pt_fields.append(QgsField("pt_id", QVariant.Int))
        pt_fields.append(QgsField("chain_m", QVariant.Double, len=12, prec=2))
        pt_fields.append(QgsField("x", QVariant.Double, len=14, prec=3))
        pt_fields.append(QgsField("y", QVariant.Double, len=14, prec=3))
        pt_fields.append(QgsField("z", QVariant.Double, len=12, prec=3))
        pt_fields.append(QgsField("facc_m2", QVariant.Double, len=14, prec=2))
        pt_fields.append(QgsField("is_drain", QVariant.Int))
        pt_fields.append(QgsField("offset_m", QVariant.Double, len=12, prec=3))

        pt_sink, pt_dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT_POINTS,
            context,
            pt_fields,
            QgsWkbTypes.Point,
            dem.crs()
        )

        if pt_sink is None:
            raise QgsProcessingException("No se pudo crear la salida de puntos GNSS.")

        dr_fields = QgsFields()
        dr_fields.append(QgsField("drain_id", QVariant.Int))
        dr_fields.append(QgsField("acc_m2", QVariant.Double, len=14, prec=2))
        dr_fields.append(QgsField("acc_cells", QVariant.Double, len=14, prec=0))

        dr_sink, dr_dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT_DRAINAGE,
            context,
            dr_fields,
            QgsWkbTypes.LineString,
            dem.crs()
        )

        if dr_sink is None:
            raise QgsProcessingException("No se pudo crear la salida de drenajes potenciales.")

        self._write_drainage_lines(
            hydro=hydro,
            mask_geom=valid_mask,
            fields=dr_fields,
            sink=dr_sink,
            feedback=feedback
        )

        line_id = 1
        total = (2 * n_offsets) + 1
        step = 0

        offset_generated_count = 0
        raw_part_count = 0
        short_reject_count = 0
        accepted_line_count = 0

        for i in range(-n_offsets, n_offsets + 1):
            if feedback.isCanceled():
                break

            offset_m = i * spacing

            if i == 0:
                g_off = QgsGeometry(mother)
            else:
                try:
                    g_off = QgsGeometry(
                        mother.offsetCurve(
                            offset_m,
                            8,
                            Qgis.JoinStyle.Round,
                            2.0
                        )
                    )
                except Exception as e:
                    feedback.pushWarning(
                        f"No se pudo generar offset {offset_m:.3f} m: {str(e)}"
                    )
                    step += 1
                    feedback.setProgress(int((step / total) * 100))
                    continue

            offset_generated_count += 1

            if g_off is None or g_off.isEmpty():
                step += 1
                feedback.setProgress(int((step / total) * 100))
                continue

            try:
                if not g_off.isGeosValid():
                    g_off = g_off.makeValid()
            except Exception:
                pass

            try:
                g_clip = g_off.intersection(valid_mask)
            except Exception as e:
                feedback.pushWarning(
                    f"Error recortando offset {offset_m:.3f} m: {str(e)}"
                )
                step += 1
                feedback.setProgress(int((step / total) * 100))
                continue

            if g_clip is None or g_clip.isEmpty():
                step += 1
                feedback.setProgress(int((step / total) * 100))
                continue

            raw_parts = self._explode_to_lines(g_clip)
            raw_part_count += len(raw_parts)

            for raw_part in raw_parts:
                if raw_part is None or raw_part.isEmpty():
                    continue

                if raw_part.length() < min_length:
                    short_reject_count += 1
                    continue

                split_parts = self._split_line_by_max_length(
                    geom=raw_part,
                    max_length=max_length
                )

                for part in split_parts:
                    if part is None or part.isEmpty():
                        continue

                    length_m = part.length()

                    if length_m < min_length:
                        short_reject_count += 1
                        continue

                    slope_data = self._compute_line_profile_metrics(
                        line_geom=part,
                        dem_layer=dem,
                        densify_m=densify,
                        max_slope_pct=max_slope
                    )

                    radius_min_val = self._minimum_radius(part)

                    hyd_data = self._compute_hydrology_metrics_for_line(
                        line_geom=part,
                        hydro=hydro,
                        densify_m=densify
                    )

                    risk = self._risk_class(
                        slope_max_pct=slope_data["slope_max"],
                        radius_min=radius_min_val,
                        min_radius=min_radius,
                        hyd_cls=hyd_data["hyd_cls"]
                    )

                    icl, status, review = self._calculate_preliminary_icl(
                        length_m=length_m,
                        min_length=min_length,
                        max_length=max_length,
                        slope_max_pct=slope_data["slope_max"],
                        max_slope_pct=max_slope,
                        radius_min=radius_min_val,
                        min_radius=min_radius,
                        hyd_cls=hyd_data["hyd_cls"],
                        drain_hits=hyd_data["drain_hits"]
                    )

                    f = QgsFeature(fields)
                    f.setGeometry(part)

                    f["line_id"] = line_id
                    f["offset_m"] = float(offset_m)
                    f["length_m"] = float(length_m)

                    f["z_ini"] = slope_data["z_ini"]
                    f["z_fin"] = slope_data["z_fin"]
                    f["z_min"] = slope_data["z_min"]
                    f["z_max"] = slope_data["z_max"]
                    f["dz_total"] = slope_data["dz_total"]

                    f["slope_avg"] = slope_data["slope_avg"]
                    f["slope_max"] = slope_data["slope_max"]
                    f["crit_len_m"] = slope_data["crit_len_m"]
                    f["crit_len_pct"] = slope_data["crit_len_pct"]

                    f["radius_min"] = radius_min_val
                    f["facc_max"] = hyd_data["facc_max"]
                    f["facc_mean"] = hyd_data["facc_mean"]
                    f["drain_hits"] = hyd_data["drain_hits"]
                    f["hyd_cls"] = hyd_data["hyd_cls"]

                    f["risk_cls"] = risk
                    f["icl"] = icl
                    f["status"] = status
                    f["review"] = review

                    sink.addFeature(f, QgsFeatureSink.FastInsert)
                    accepted_line_count += 1

                    self._write_stakeout_points(
                        line_geom=part,
                        dem_layer=dem,
                        line_id=line_id,
                        offset_m=offset_m,
                        spacing_m=densify,
                        fields=pt_fields,
                        sink=pt_sink,
                        hydro=hydro
                    )

                    line_id += 1

            step += 1
            feedback.setProgress(int((step / total) * 100))

        feedback.pushInfo(f"Offsets generados: {offset_generated_count:,}")
        feedback.pushInfo(f"Partes crudas generadas despues de recorte: {raw_part_count:,}")
        feedback.pushInfo(f"Partes descartadas por longitud: {short_reject_count:,}")
        feedback.pushInfo(f"Lineas aceptadas: {accepted_line_count:,}")
        feedback.pushInfo(f"Lineas generadas: {line_id - 1}")

        if accepted_line_count == 0:
            feedback.pushWarning(
                "No se generaron lineas LDI. Posibles causas: "
                "MIN_LENGTH demasiado alto, mascara demasiado pequena, "
                "linea madre inadecuada, intervalo de curvas insuficiente, "
                "o offsets fuera del area valida."
            )

        return {
            self.OUTPUT: dest_id,
            self.OUTPUT_POINTS: pt_dest_id,
            self.OUTPUT_DRAINAGE: dr_dest_id
        }

    def _validate_dem_basic(self, dem, spacing, densify, feedback):
        provider = dem.dataProvider()

        if dem.width() <= 0 or dem.height() <= 0:
            raise QgsProcessingException("El DEM tiene dimensiones invalidas.")

        px = abs(dem.rasterUnitsPerPixelX())
        py = abs(dem.rasterUnitsPerPixelY())

        if px <= 0 or py <= 0:
            raise QgsProcessingException("El tamano de pixel del DEM es invalido.")

        feedback.pushInfo(f"Resolucion DEM: {px:.3f} m x {py:.3f} m")

        if max(px, py) > spacing / 3.0:
            feedback.pushWarning(
                "La resolucion del DEM puede ser insuficiente para el espaciamiento solicitado. "
                f"Pixel actual={max(px, py):.2f} m, spacing={spacing:.2f} m."
            )

        if densify < max(px, py):
            feedback.pushWarning(
                "La distancia de densificacion es menor que el tamano de pixel. "
                "Puede generar sobremuestreo sin informacion real adicional."
            )

        stats = provider.bandStatistics(
            1,
            QgsRasterBandStats.All,
            dem.extent(),
            0
        )

        if math.isnan(stats.minimumValue) or math.isnan(stats.maximumValue):
            raise QgsProcessingException("El DEM no tiene estadisticas validas.")

        if stats.maximumValue <= stats.minimumValue:
            raise QgsProcessingException("El rango altimetrico del DEM es invalido.")

        feedback.pushInfo(
            f"Rango altimetrico DEM: {stats.minimumValue:.3f} m a {stats.maximumValue:.3f} m"
        )

    def _build_hydrology_model(self, dem_layer, flow_threshold_area, max_cells, feedback):
        width = dem_layer.width()
        height = dem_layer.height()
        n_cells = width * height

        if n_cells > max_cells:
            raise QgsProcessingException(
                f"El DEM tiene {n_cells:,} celdas, superior al limite configurado "
                f"({max_cells:,}). Recorte el DEM al area de diseno o aumente MAX_HYDRO_CELLS."
            )

        extent = dem_layer.extent()
        provider = dem_layer.dataProvider()

        px = abs(dem_layer.rasterUnitsPerPixelX())
        py = abs(dem_layer.rasterUnitsPerPixelY())
        cell_area = px * py

        feedback.pushInfo(
            f"Hidrologia DEM: {width} columnas x {height} filas = {n_cells:,} celdas."
        )

        feedback.pushInfo(
            f"Tamano de celda: {px:.4f} m x {py:.4f} m. Area celda: {cell_area:.4f} m2."
        )

        block = provider.block(1, extent, width, height)
        arr = np.full((height, width), np.nan, dtype=np.float64)

        nodata = None
        try:
            nodata = provider.sourceNoDataValue(1)
        except Exception:
            nodata = None

        for r in range(height):
            for c in range(width):
                is_nodata = False

                try:
                    if block.isNoData(r, c):
                        is_nodata = True
                except Exception:
                    is_nodata = False

                if is_nodata:
                    continue

                try:
                    v = float(block.value(r, c))
                except Exception:
                    continue

                if nodata is not None:
                    try:
                        if abs(v - float(nodata)) < 1e-12:
                            continue
                    except Exception:
                        pass

                if math.isfinite(v):
                    arr[r, c] = v

        valid = np.isfinite(arr)
        valid_count = int(np.count_nonzero(valid))

        feedback.pushInfo(f"Celdas validas para hidrologia: {valid_count:,}")

        if valid_count < 10:
            raise QgsProcessingException("El DEM no contiene suficientes celdas validas.")

        feedback.pushInfo("Aplicando relleno hidrologico basico Priority-Flood con epsilon...")
        filled = self._priority_flood_fill(arr, valid)

        feedback.pushInfo("Calculando direccion de flujo D8 hibrida: DEM original + DEM rellenado...")
        receiver, receiver_dist = self._compute_d8_receivers_hybrid(
            original=arr,
            filled=filled,
            valid=valid,
            px=px,
            py=py
        )

        receiver_count = int(np.count_nonzero(receiver >= 0))
        feedback.pushInfo(f"Celdas con receptor D8 valido: {receiver_count:,}")

        feedback.pushInfo("Calculando acumulacion de flujo...")
        acc = self._compute_flow_accumulation(receiver, valid)

        threshold_cells = max(1.0, flow_threshold_area / cell_area)
        drainage_mask = (acc >= threshold_cells) & valid

        max_acc_cells = float(np.nanmax(acc[valid]))
        max_acc_area = max_acc_cells * cell_area
        mean_acc_area = float(np.nanmean(acc[valid]) * cell_area)
        drainage_cell_count = int(np.count_nonzero(drainage_mask))

        feedback.pushInfo(
            f"Acumulacion maxima calculada: {max_acc_cells:.0f} celdas = "
            f"{max_acc_area:.2f} m2."
        )

        feedback.pushInfo(
            f"Acumulacion media calculada: {mean_acc_area:.2f} m2."
        )

        feedback.pushInfo(
            f"Umbral drenaje: {flow_threshold_area:.2f} m2 "
            f"({threshold_cells:.1f} celdas)."
        )

        feedback.pushInfo(
            f"Celdas que superan el umbral antes de mascara: {drainage_cell_count:,}"
        )

        if drainage_cell_count == 0:
            feedback.pushWarning(
                "No hay celdas que superen el umbral de drenaje. "
                "Pruebe bajando FLOW_THRESHOLD_AREA a 10, 25, 50 o 100 m2."
            )

        return {
            "arr": arr,
            "filled": filled,
            "valid": valid,
            "receiver": receiver,
            "receiver_dist": receiver_dist,
            "acc": acc,
            "drainage_mask": drainage_mask,
            "threshold_area": flow_threshold_area,
            "threshold_cells": threshold_cells,
            "cell_area": cell_area,
            "px": px,
            "py": py,
            "width": width,
            "height": height,
            "extent": extent,
            "xmin": extent.xMinimum(),
            "xmax": extent.xMaximum(),
            "ymin": extent.yMinimum(),
            "ymax": extent.yMaximum(),
            "max_acc_area": max_acc_area,
            "mean_acc_area": mean_acc_area,
            "drainage_cell_count": drainage_cell_count
        }

    def _priority_flood_fill(self, arr, valid):
        h, w = arr.shape
        filled = np.array(arr, copy=True)
        visited = np.zeros((h, w), dtype=bool)
        heap = []
        eps = 1e-6

        for r in range(h):
            for c in (0, w - 1):
                if valid[r, c] and not visited[r, c]:
                    visited[r, c] = True
                    heapq.heappush(heap, (filled[r, c], r, c))

        for c in range(w):
            for r in (0, h - 1):
                if valid[r, c] and not visited[r, c]:
                    visited[r, c] = True
                    heapq.heappush(heap, (filled[r, c], r, c))

        neigh = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        while heap:
            z, r, c = heapq.heappop(heap)

            for dr, dc in neigh:
                rr = r + dr
                cc = c + dc

                if rr < 0 or rr >= h or cc < 0 or cc >= w:
                    continue

                if visited[rr, cc] or not valid[rr, cc]:
                    continue

                visited[rr, cc] = True

                if filled[rr, cc] <= z:
                    filled[rr, cc] = z + eps

                heapq.heappush(heap, (filled[rr, cc], rr, cc))

        return filled

    def _compute_d8_receivers_hybrid(self, original, filled, valid, px, py):
        h, w = filled.shape
        receiver = np.full((h, w), -1, dtype=np.int64)
        receiver_dist = np.full((h, w), np.nan, dtype=np.float64)

        diag = math.hypot(px, py)

        neigh = [
            (-1, -1, diag),
            (-1, 0, py),
            (-1, 1, diag),
            (0, -1, px),
            (0, 1, px),
            (1, -1, diag),
            (1, 0, py),
            (1, 1, diag)
        ]

        for r in range(h):
            for c in range(w):
                if not valid[r, c]:
                    continue

                z_orig = original[r, c]
                best_slope = 0.0
                best_idx = -1
                best_dist = np.nan

                if math.isfinite(z_orig):
                    for dr, dc, dist in neigh:
                        rr = r + dr
                        cc = c + dc

                        if rr < 0 or rr >= h or cc < 0 or cc >= w:
                            continue

                        if not valid[rr, cc]:
                            continue

                        z2 = original[rr, cc]

                        if not math.isfinite(z2):
                            continue

                        dz = z_orig - z2

                        if dz <= 0:
                            continue

                        s = dz / dist

                        if s > best_slope:
                            best_slope = s
                            best_idx = rr * w + cc
                            best_dist = dist

                if best_idx < 0:
                    z_fill = filled[r, c]
                    best_slope_fill = 0.0

                    for dr, dc, dist in neigh:
                        rr = r + dr
                        cc = c + dc

                        if rr < 0 or rr >= h or cc < 0 or cc >= w:
                            continue

                        if not valid[rr, cc]:
                            continue

                        dz = z_fill - filled[rr, cc]

                        if dz <= 0:
                            continue

                        s = dz / dist

                        if s > best_slope_fill:
                            best_slope_fill = s
                            best_idx = rr * w + cc
                            best_dist = dist

                receiver[r, c] = best_idx
                receiver_dist[r, c] = best_dist

        return receiver, receiver_dist

    def _compute_flow_accumulation(self, receiver, valid):
        h, w = receiver.shape
        n = h * w

        acc = np.zeros(n, dtype=np.float64)
        indeg = np.zeros(n, dtype=np.int32)
        rec_flat = receiver.reshape(-1)
        valid_flat = valid.reshape(-1)

        for idx in range(n):
            if valid_flat[idx]:
                acc[idx] = 1.0

        for idx in range(n):
            if not valid_flat[idx]:
                continue

            j = rec_flat[idx]

            if j >= 0:
                indeg[j] += 1

        queue = []

        for idx in range(n):
            if valid_flat[idx] and indeg[idx] == 0:
                queue.append(idx)

        head = 0

        while head < len(queue):
            idx = queue[head]
            head += 1

            j = rec_flat[idx]

            if j >= 0:
                acc[j] += acc[idx]
                indeg[j] -= 1

                if indeg[j] == 0:
                    queue.append(j)

        return acc.reshape((h, w))

    def _xy_to_rowcol(self, hydro, x, y):
        xmin = hydro["xmin"]
        ymax = hydro["ymax"]
        px = hydro["px"]
        py = hydro["py"]
        width = hydro["width"]
        height = hydro["height"]

        c = int((x - xmin) / px)
        r = int((ymax - y) / py)

        if r < 0 or r >= height or c < 0 or c >= width:
            return None, None

        return r, c

    def _rowcol_to_xy(self, hydro, r, c):
        x = hydro["xmin"] + (c + 0.5) * hydro["px"]
        y = hydro["ymax"] - (r + 0.5) * hydro["py"]

        return x, y

    def _sample_flow_acc_area(self, hydro, x, y):
        r, c = self._xy_to_rowcol(hydro, x, y)

        if r is None:
            return None

        if not hydro["valid"][r, c]:
            return None

        return float(hydro["acc"][r, c] * hydro["cell_area"])

    def _compute_hydrology_metrics_for_line(self, line_geom, hydro, densify_m):
        result = {
            "facc_max": None,
            "facc_mean": None,
            "drain_hits": 0,
            "hyd_cls": "NA"
        }

        if line_geom is None or line_geom.isEmpty():
            return result

        try:
            g = line_geom.densifyByDistance(densify_m)
        except Exception:
            g = QgsGeometry(line_geom)

        vals = []
        hits = 0

        for v in g.vertices():
            area = self._sample_flow_acc_area(hydro, v.x(), v.y())

            if area is None:
                continue

            vals.append(area)

            if area >= hydro["threshold_area"]:
                hits += 1

        if not vals:
            return result

        facc_max = max(vals)
        facc_mean = sum(vals) / len(vals)

        result["facc_max"] = facc_max
        result["facc_mean"] = facc_mean
        result["drain_hits"] = hits
        result["hyd_cls"] = self._hydrologic_class(
            facc_max=facc_max,
            drain_hits=hits,
            threshold_area=hydro["threshold_area"]
        )

        return result

    def _hydrologic_class(self, facc_max, drain_hits, threshold_area):
        if facc_max is None:
            return "NA"

        ratio = facc_max / max(threshold_area, 1e-9)

        if drain_hits > 0 and ratio >= 1.0:
            if ratio >= 5.0:
                return "E"
            if ratio >= 2.0:
                return "D"
            return "C"

        if ratio < 0.25:
            return "A"

        if ratio < 0.50:
            return "B"

        if ratio < 1.00:
            return "C"

        if ratio < 2.00:
            return "D"

        return "E"

    def _write_drainage_lines(self, hydro, mask_geom, fields, sink, feedback):
        drain_id = 1
        candidate_count = 0
        exported_count = 0
        skipped_by_mask = 0
        skipped_no_receiver = 0

        h = hydro["height"]
        w = hydro["width"]

        drainage_mask = hydro["drainage_mask"]
        receiver = hydro["receiver"]
        acc = hydro["acc"]
        cell_area = hydro["cell_area"]

        for r in range(h):
            for c in range(w):
                if not drainage_mask[r, c]:
                    continue

                candidate_count += 1

                rec = int(receiver[r, c])

                if rec < 0:
                    skipped_no_receiver += 1
                    continue

                rr = rec // w
                cc = rec % w

                if rr < 0 or rr >= h or cc < 0 or cc >= w:
                    skipped_no_receiver += 1
                    continue

                x1, y1 = self._rowcol_to_xy(hydro, r, c)
                x2, y2 = self._rowcol_to_xy(hydro, rr, cc)

                geom = QgsGeometry.fromPolylineXY([
                    QgsPointXY(x1, y1),
                    QgsPointXY(x2, y2)
                ])

                try:
                    if mask_geom is not None and not geom.intersects(mask_geom):
                        skipped_by_mask += 1
                        continue
                except Exception:
                    pass

                f = QgsFeature(fields)
                f.setGeometry(geom)
                f["drain_id"] = drain_id
                f["acc_m2"] = float(acc[r, c] * cell_area)
                f["acc_cells"] = float(acc[r, c])

                sink.addFeature(f, QgsFeatureSink.FastInsert)

                drain_id += 1
                exported_count += 1

        feedback.pushInfo(f"Celdas candidatas a drenaje: {candidate_count:,}")
        feedback.pushInfo(f"Drenajes omitidos sin receptor D8: {skipped_no_receiver:,}")
        feedback.pushInfo(f"Drenajes omitidos por mascara: {skipped_by_mask:,}")
        feedback.pushInfo(f"Drenajes potenciales exportados: {exported_count:,}")

        if exported_count == 0:
            feedback.pushWarning(
                "La capa de drenajes potenciales quedo vacia. "
                "Revise en el log: acumulacion maxima, celdas candidatas, "
                "omisiones por mascara y umbral de area contribuyente."
            )

    def _alg_exists(self, alg_id):
        return QgsApplication.processingRegistry().algorithmById(alg_id) is not None

    def _create_contours_layer(self, dem, interval, context, feedback):
        candidates = [
            "native:contour",
            "qgis:contour",
            "gdal:contour"
        ]

        selected = next((a for a in candidates if self._alg_exists(a)), None)

        if selected is None:
            raise QgsProcessingException(
                "No se encontro algoritmo de contornos. "
                "Habilite proveedores Processing de QGIS/GDAL."
            )

        feedback.pushInfo(f"Algoritmo de contornos seleccionado: {selected}")

        if selected in ("native:contour", "qgis:contour"):
            res = processing.run(
                selected,
                {
                    "INPUT": dem,
                    "BAND": 1,
                    "INTERVAL": interval,
                    "OFFSET": 0,
                    "FIELD_NAME": "ELEV",
                    "CREATE_3D": False,
                    "IGNORE_NODATA": False,
                    "NODATA": None,
                    "OUTPUT": "TEMPORARY_OUTPUT"
                },
                context=context,
                feedback=feedback
            )

            lyr = self._resolve_vector_layer(
                res.get("OUTPUT"),
                context,
                "contours_tmp"
            )

            return lyr

        tmp_shp = QgsProcessingUtils.generateTempFilename("contours_tmp.shp")

        res = processing.run(
            "gdal:contour",
            {
                "INPUT": dem.source(),
                "BAND": 1,
                "INTERVAL": interval,
                "FIELD_NAME": "ELEV",
                "CREATE_3D": False,
                "IGNORE_NODATA": False,
                "NODATA": None,
                "OFFSET": 0,
                "OUTPUT": tmp_shp
            },
            context=context,
            feedback=feedback
        )

        out_obj = res.get("OUTPUT", tmp_shp)

        lyr = self._resolve_vector_layer(
            out_obj,
            context,
            "contours_tmp"
        )

        if (lyr is None or not lyr.isValid()) and tmp_shp:
            lyr = QgsVectorLayer(tmp_shp, "contours_tmp", "ogr")

        return lyr

    def _resolve_vector_layer(self, out_obj, context, name="tmp_layer"):
        if out_obj is None:
            return None

        if hasattr(out_obj, "getFeatures"):
            return out_obj

        if isinstance(out_obj, str):
            lyr = QgsProcessingUtils.mapLayerFromString(out_obj, context)

            if lyr and lyr.isValid():
                return lyr

            lyr = QgsVectorLayer(out_obj, name, "ogr")

            if lyr.isValid():
                return lyr

        return None

    def _build_mask_geometry(self, dem_layer, mask_layer):
        dem_crs = dem_layer.crs()

        if mask_layer:
            geoms = []
            ct = None

            if mask_layer.crs() != dem_crs:
                ct = QgsCoordinateTransform(
                    mask_layer.crs(),
                    dem_crs,
                    QgsProject.instance()
                )

            for ft in mask_layer.getFeatures():
                g = QgsGeometry(ft.geometry())

                if g is None or g.isEmpty():
                    continue

                if ct:
                    g.transform(ct)

                if not g.isGeosValid():
                    g = g.makeValid()

                if not g.isEmpty():
                    geoms.append(g)

            if not geoms:
                return None

            out = QgsGeometry.unaryUnion(geoms)

            if out is not None and not out.isEmpty():
                if not out.isGeosValid():
                    out = out.makeValid()

            return out

        ext = dem_layer.extent()

        ring = [
            QgsPointXY(ext.xMinimum(), ext.yMinimum()),
            QgsPointXY(ext.xMaximum(), ext.yMinimum()),
            QgsPointXY(ext.xMaximum(), ext.yMaximum()),
            QgsPointXY(ext.xMinimum(), ext.yMaximum()),
            QgsPointXY(ext.xMinimum(), ext.yMinimum())
        ]

        return QgsGeometry.fromPolygonXY([ring])

    def _build_exclusion_geometry(self, dem_layer, exclusion_layer, buffer_m, feedback):
        if exclusion_layer is None:
            return None

        dem_crs = dem_layer.crs()
        geoms = []
        ct = None

        if exclusion_layer.crs() != dem_crs:
            ct = QgsCoordinateTransform(
                exclusion_layer.crs(),
                dem_crs,
                QgsProject.instance()
            )

        for ft in exclusion_layer.getFeatures():
            g = QgsGeometry(ft.geometry())

            if g is None or g.isEmpty():
                continue

            if ct:
                g.transform(ct)

            if buffer_m > 0:
                g = g.buffer(buffer_m, 12)

            if not g.isGeosValid():
                g = g.makeValid()

            if not g.isEmpty():
                geoms.append(g)

        if not geoms:
            return None

        exclusion = QgsGeometry.unaryUnion(geoms)

        if exclusion is None or exclusion.isEmpty():
            return None

        if not exclusion.isGeosValid():
            exclusion = exclusion.makeValid()

        feedback.pushInfo("Geometria de exclusion construida correctamente.")

        return exclusion

    def _estimate_mid_elevation_from_contours(
        self,
        contour_layer,
        mask_geom,
        fallback_dem,
        feedback
    ):
        elev_idx = contour_layer.fields().indexFromName("ELEV")
        values = []

        if elev_idx >= 0:
            for ft in contour_layer.getFeatures():
                g = ft.geometry()

                if g is None or g.isEmpty():
                    continue

                try:
                    if not g.intersects(mask_geom):
                        continue
                except Exception:
                    continue

                elev = ft["ELEV"]

                if elev is not None:
                    try:
                        values.append(float(elev))
                    except Exception:
                        pass

        if values:
            values.sort()
            mid = values[len(values) // 2]
            feedback.pushInfo(
                f"Cota media estimada desde curvas dentro de mascara: {mid:.3f} m"
            )
            return mid

        stats = fallback_dem.dataProvider().bandStatistics(
            1,
            QgsRasterBandStats.All,
            fallback_dem.extent(),
            0
        )

        mid = (stats.minimumValue + stats.maximumValue) / 2.0

        feedback.pushWarning(
            "No se pudo estimar cota media desde curvas en mascara. "
            "Se usa rango completo del DEM."
        )

        return mid

    def _select_mother_line(
        self,
        contour_layer,
        mask_geom,
        z_mid,
        dem,
        densify,
        min_radius,
        max_slope,
        hydro,
        flow_threshold_area,
        min_length,
        feedback
    ):
        best_geom = None
        best_score = -1.0

        elev_idx = contour_layer.fields().indexFromName("ELEV")

        if elev_idx < 0:
            feedback.pushWarning("La capa de contornos no tiene campo ELEV.")
            return None

        contour_count = 0
        part_count = 0
        short_count = 0
        evaluated_count = 0

        longest_geom = None
        longest_len = 0.0

        for ft in contour_layer.getFeatures():
            contour_count += 1

            g = ft.geometry()

            if g is None or g.isEmpty():
                continue

            try:
                g_clip = g.intersection(mask_geom)
            except Exception:
                continue

            if g_clip is None or g_clip.isEmpty():
                continue

            elev = ft["ELEV"]

            if elev is None:
                elev = z_mid

            try:
                elev = float(elev)
            except Exception:
                elev = z_mid

            parts = self._explode_to_lines(g_clip)

            for part in parts:
                part_count += 1

                if part is None or part.isEmpty():
                    continue

                l = part.length()

                if l > longest_len:
                    longest_len = l
                    longest_geom = QgsGeometry(part)

                if l < min_length:
                    short_count += 1
                    continue

                evaluated_count += 1

                slope_data = self._compute_line_profile_metrics(
                    line_geom=part,
                    dem_layer=dem,
                    densify_m=densify,
                    max_slope_pct=max_slope
                )

                slope_max = slope_data["slope_max"]
                radius_min_val = self._minimum_radius(part)

                hyd_data = self._compute_hydrology_metrics_for_line(
                    line_geom=part,
                    hydro=hydro,
                    densify_m=densify
                )

                facc_max = hyd_data["facc_max"]

                score_length = min(l / 200.0, 1.0)
                score_elev = 1.0 / (1.0 + abs(elev - z_mid))

                if slope_max is None:
                    score_slope = 0.0
                else:
                    denom = max(max_slope * 2.0, 0.01)
                    score_slope = max(0.0, 1.0 - (slope_max / denom))

                if radius_min_val is None:
                    score_radius = 0.5
                else:
                    score_radius = min(radius_min_val / min_radius, 1.0)

                if facc_max is None:
                    score_hydro = 0.5
                else:
                    score_hydro = max(
                        0.0,
                        1.0 - (facc_max / max(flow_threshold_area * 2.0, 1e-9))
                    )

                score = (
                    0.30 * score_length +
                    0.20 * score_slope +
                    0.20 * score_radius +
                    0.15 * score_hydro +
                    0.15 * score_elev
                )

                if score > best_score:
                    best_score = score
                    best_geom = QgsGeometry(part)

        feedback.pushInfo(f"Curvas evaluadas: {contour_count:,}")
        feedback.pushInfo(f"Partes de contorno dentro de mascara: {part_count:,}")
        feedback.pushInfo(f"Partes descartadas por longitud menor a MIN_LENGTH: {short_count:,}")
        feedback.pushInfo(f"Partes candidatas evaluadas para linea madre: {evaluated_count:,}")

        if best_geom is not None and not best_geom.isEmpty():
            feedback.pushInfo(
                f"Linea madre seleccionada. Longitud: {best_geom.length():.2f} m. "
                f"Score: {best_score:.3f}"
            )
            return best_geom

        if longest_geom is not None and not longest_geom.isEmpty():
            feedback.pushWarning(
                "No se encontro linea madre que cumpliera todos los criterios. "
                "Se usara como respaldo la linea de contorno mas larga dentro de la mascara."
            )
            feedback.pushWarning(
                f"Linea madre de respaldo. Longitud: {longest_geom.length():.2f} m."
            )
            return longest_geom

        return None

    def _explode_to_lines(self, geom):
        out = []

        if geom is None or geom.isEmpty():
            return out

        geom_type = QgsWkbTypes.geometryType(geom.wkbType())

        if geom_type == QgsWkbTypes.LineGeometry:
            if geom.isMultipart():
                try:
                    mpl = geom.asMultiPolyline()
                except Exception:
                    mpl = []

                if mpl:
                    for pl in mpl:
                        if pl and len(pl) >= 2:
                            out.append(QgsGeometry.fromPolylineXY(pl))

                return out

            try:
                pl = geom.asPolyline()
            except Exception:
                pl = []

            if pl and len(pl) >= 2:
                out.append(QgsGeometry.fromPolylineXY(pl))

            return out

        try:
            collection = geom.asGeometryCollection()

            if collection:
                for sub in collection:
                    out.extend(self._explode_to_lines(sub))

                return out
        except Exception:
            pass

        try:
            for part in geom.constParts():
                sub = QgsGeometry(part.clone())
                out.extend(self._explode_to_lines(sub))
        except Exception:
            pass

        return out

    def _chaikin_geometry(self, geom, iterations):
        if geom is None or geom.isEmpty():
            return geom

        try:
            line = geom.asPolyline()
        except Exception:
            line = []

        if not line:
            return geom

        pts = [QgsPointXY(p) for p in line]

        for _ in range(max(0, iterations)):
            if len(pts) < 3:
                break

            new_pts = [pts[0]]

            for i in range(len(pts) - 1):
                p0 = pts[i]
                p1 = pts[i + 1]

                q = QgsPointXY(
                    0.75 * p0.x() + 0.25 * p1.x(),
                    0.75 * p0.y() + 0.25 * p1.y()
                )

                r = QgsPointXY(
                    0.25 * p0.x() + 0.75 * p1.x(),
                    0.25 * p0.y() + 0.75 * p1.y()
                )

                new_pts.append(q)
                new_pts.append(r)

            new_pts.append(pts[-1])
            pts = new_pts

        return QgsGeometry.fromPolylineXY(pts)

    def _split_line_by_max_length(self, geom, max_length):
        if geom is None or geom.isEmpty():
            return []

        length = geom.length()

        if length <= max_length:
            return [geom]

        n = int(math.ceil(length / max_length))
        parts = []

        for i in range(n):
            start_m = i * max_length
            end_m = min((i + 1) * max_length, length)

            sub = self._line_substring(
                geom=geom,
                start_m=start_m,
                end_m=end_m
            )

            if sub is not None and not sub.isEmpty() and sub.length() > 0:
                parts.append(sub)

        return parts

    def _line_substring(self, geom, start_m, end_m):
        if geom is None or geom.isEmpty():
            return None

        pts = [QgsPointXY(v.x(), v.y()) for v in geom.vertices()]

        if len(pts) < 2 or end_m <= start_m:
            return None

        cum = [0.0]

        for i in range(len(pts) - 1):
            d = math.hypot(
                pts[i + 1].x() - pts[i].x(),
                pts[i + 1].y() - pts[i].y()
            )

            cum.append(cum[-1] + d)

        total = cum[-1]

        if total <= 0:
            return None

        start_m = max(0.0, min(start_m, total))
        end_m = max(0.0, min(end_m, total))

        if end_m <= start_m:
            return None

        out_pts = []

        p_start = self._interpolate_point_by_m(pts, cum, start_m)
        p_end = self._interpolate_point_by_m(pts, cum, end_m)

        if p_start is None or p_end is None:
            return None

        out_pts.append(p_start)

        for i in range(1, len(pts) - 1):
            if cum[i] > start_m and cum[i] < end_m:
                out_pts.append(pts[i])

        out_pts.append(p_end)

        if len(out_pts) < 2:
            return None

        return QgsGeometry.fromPolylineXY(out_pts)

    def _interpolate_point_by_m(self, pts, cum, m):
        if not pts or not cum:
            return None

        if m <= 0:
            return pts[0]

        if m >= cum[-1]:
            return pts[-1]

        for i in range(len(cum) - 1):
            if cum[i] <= m <= cum[i + 1]:
                seg_len = cum[i + 1] - cum[i]

                if seg_len <= 0:
                    return pts[i]

                t = (m - cum[i]) / seg_len

                x = pts[i].x() + t * (pts[i + 1].x() - pts[i].x())
                y = pts[i].y() + t * (pts[i + 1].y() - pts[i].y())

                return QgsPointXY(x, y)

        return pts[-1]

    def _compute_line_profile_metrics(
        self,
        line_geom,
        dem_layer,
        densify_m,
        max_slope_pct
    ):
        result = {
            "z_ini": None,
            "z_fin": None,
            "z_min": None,
            "z_max": None,
            "dz_total": None,
            "slope_avg": None,
            "slope_max": None,
            "crit_len_m": 0.0,
            "crit_len_pct": 0.0
        }

        if line_geom is None or line_geom.isEmpty():
            return result

        try:
            g = line_geom.densifyByDistance(densify_m)
        except Exception:
            g = QgsGeometry(line_geom)

        vertices = [v for v in g.vertices()]

        if len(vertices) < 2:
            return result

        provider = dem_layer.dataProvider()
        z_vals = []

        for v in vertices:
            try:
                z, ok = provider.sample(QgsPointXY(v.x(), v.y()), 1)
            except Exception:
                z, ok = None, False

            if not ok or z is None:
                z_vals.append(None)
            else:
                try:
                    z_vals.append(float(z))
                except Exception:
                    z_vals.append(None)

        valid_z = [z for z in z_vals if z is not None]

        if len(valid_z) < 2:
            return result

        result["z_ini"] = valid_z[0]
        result["z_fin"] = valid_z[-1]
        result["z_min"] = min(valid_z)
        result["z_max"] = max(valid_z)
        result["dz_total"] = valid_z[-1] - valid_z[0]

        seg_abs = []
        total_valid_len = 0.0
        crit_len = 0.0

        first_valid_index = None
        last_valid_index = None

        for i, z in enumerate(z_vals):
            if z is not None:
                if first_valid_index is None:
                    first_valid_index = i

                last_valid_index = i

        dist_between_valid_extremes = 0.0

        for i in range(len(vertices) - 1):
            dx = vertices[i + 1].x() - vertices[i].x()
            dy = vertices[i + 1].y() - vertices[i].y()
            d = math.hypot(dx, dy)

            if d <= 0:
                continue

            if (
                first_valid_index is not None and
                last_valid_index is not None and
                i >= first_valid_index and
                i < last_valid_index
            ):
                dist_between_valid_extremes += d

            z1 = z_vals[i]
            z2 = z_vals[i + 1]

            if z1 is None or z2 is None:
                continue

            s_pct = abs((z2 - z1) / d) * 100.0

            seg_abs.append(s_pct)
            total_valid_len += d

            if s_pct > max_slope_pct:
                crit_len += d

        if not seg_abs:
            return result

        result["slope_max"] = max(seg_abs)

        if dist_between_valid_extremes > 0:
            result["slope_avg"] = (
                (valid_z[-1] - valid_z[0]) / dist_between_valid_extremes
            ) * 100.0

        result["crit_len_m"] = crit_len

        if total_valid_len > 0:
            result["crit_len_pct"] = 100.0 * crit_len / total_valid_len

        return result

    def _minimum_radius(self, geom):
        if geom is None or geom.isEmpty():
            return None

        try:
            g = geom.densifyByDistance(2.0)
        except Exception:
            g = QgsGeometry(geom)

        pts = [QgsPointXY(v.x(), v.y()) for v in g.vertices()]

        if len(pts) < 3:
            return None

        radii = []

        for i in range(1, len(pts) - 1):
            p1 = pts[i - 1]
            p2 = pts[i]
            p3 = pts[i + 1]

            a = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
            b = math.hypot(p3.x() - p2.x(), p3.y() - p2.y())
            c = math.hypot(p3.x() - p1.x(), p3.y() - p1.y())

            if a <= 0 or b <= 0 or c <= 0:
                continue

            area = abs(
                (p2.x() - p1.x()) * (p3.y() - p1.y()) -
                (p3.x() - p1.x()) * (p2.y() - p1.y())
            ) / 2.0

            if area <= 1e-9:
                continue

            r = (a * b * c) / (4.0 * area)

            if math.isfinite(r):
                radii.append(r)

        if not radii:
            return None

        return min(radii)

    def _risk_class(self, slope_max_pct, radius_min, min_radius, hyd_cls):
        if slope_max_pct is None:
            cls = "NA"
        elif slope_max_pct <= 0.20:
            cls = "A"
        elif slope_max_pct <= 0.50:
            cls = "B"
        elif slope_max_pct <= 1.00:
            cls = "C"
        elif slope_max_pct <= 2.00:
            cls = "D"
        else:
            cls = "E"

        if radius_min is not None and radius_min < min_radius:
            cls = cls + "R"

        if hyd_cls in ("D", "E"):
            cls = cls + "H"

        return cls

    def _calculate_preliminary_icl(
        self,
        length_m,
        min_length,
        max_length,
        slope_max_pct,
        max_slope_pct,
        radius_min,
        min_radius,
        hyd_cls,
        drain_hits
    ):
        review = []

        if slope_max_pct is None:
            score_slope = 0
            review.append("sin pendiente")
        elif slope_max_pct <= 0.5 * max_slope_pct:
            score_slope = 30
        elif slope_max_pct <= max_slope_pct:
            score_slope = 24
        elif slope_max_pct <= 1.5 * max_slope_pct:
            score_slope = 14
            review.append("pendiente alta")
        elif slope_max_pct <= 2.0 * max_slope_pct:
            score_slope = 6
            review.append("pendiente muy alta")
        else:
            score_slope = 0
            review.append("pendiente critica")

        if radius_min is None:
            score_radius = 12
            review.append("radio no calculado")
        elif radius_min >= 1.5 * min_radius:
            score_radius = 20
        elif radius_min >= min_radius:
            score_radius = 16
        elif radius_min >= 0.75 * min_radius:
            score_radius = 8
            review.append("radio bajo")
        else:
            score_radius = 0
            review.append("radio critico")

        if length_m < min_length:
            score_length = 0
            review.append("linea corta")
        elif length_m <= max_length:
            score_length = 15
        elif length_m <= 1.25 * max_length:
            score_length = 8
            review.append("longitud alta")
        else:
            score_length = 0
            review.append("longitud critica")

        score_geom = 10

        if hyd_cls == "A":
            score_hydro = 25
        elif hyd_cls == "B":
            score_hydro = 21
        elif hyd_cls == "C":
            score_hydro = 14
            if drain_hits > 0:
                review.append("intercepta drenaje potencial")
        elif hyd_cls == "D":
            score_hydro = 6
            review.append("acumulacion alta")
        elif hyd_cls == "E":
            score_hydro = 0
            review.append("acumulacion critica")
        else:
            score_hydro = 10
            review.append("hidrologia no evaluada")

        icl = score_slope + score_radius + score_length + score_geom + score_hydro

        if icl >= 85:
            status = "ACEPTAR"
        elif icl >= 70:
            status = "REVISAR"
        elif icl >= 55:
            status = "AJUSTAR"
        else:
            status = "REDISENAR"

        return float(icl), status, "; ".join(review)

    def _write_stakeout_points(
        self,
        line_geom,
        dem_layer,
        line_id,
        offset_m,
        spacing_m,
        fields,
        sink,
        hydro
    ):
        if line_geom is None or line_geom.isEmpty():
            return

        try:
            g = line_geom.densifyByDistance(spacing_m)
        except Exception:
            g = QgsGeometry(line_geom)

        pts = [QgsPointXY(v.x(), v.y()) for v in g.vertices()]

        if len(pts) < 2:
            return

        provider = dem_layer.dataProvider()

        chain = 0.0
        pt_id = 1
        prev = None

        for p in pts:
            if prev is not None:
                chain += math.hypot(
                    p.x() - prev.x(),
                    p.y() - prev.y()
                )

            try:
                z, ok = provider.sample(p, 1)
            except Exception:
                z, ok = None, False

            z_val = float(z) if ok and z is not None else None

            facc = self._sample_flow_acc_area(hydro, p.x(), p.y())
            is_drain = 1 if facc is not None and facc >= hydro["threshold_area"] else 0

            f = QgsFeature(fields)
            f.setGeometry(QgsGeometry.fromPointXY(p))

            f["line_id"] = line_id
            f["pt_id"] = pt_id
            f["chain_m"] = float(chain)
            f["x"] = float(p.x())
            f["y"] = float(p.y())
            f["z"] = z_val
            f["facc_m2"] = facc
            f["is_drain"] = is_drain
            f["offset_m"] = float(offset_m)

            sink.addFeature(f, QgsFeatureSink.FastInsert)

            prev = p
            pt_id += 1