layer = iface.activeLayer()

# Создаем выходной слой
fields = QgsFields()
fields.append(QgsField("ONEWAY", QVariant.String))
fields.append(QgsField("MAXSPEED", QVariant.Double))  # теперь вещественный
fields.append(QgsField("FCLASS", QVariant.String))

crs = layer.crs()
out_layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", "links", "memory")
prov = out_layer.dataProvider()
prov.addAttributes(fields)
out_layer.updateFields()

def normalize_speed(v):
    if v is None:
        return None
    try:
        v = float(v)
        if v < 3.6:
            return 3.6
        return v
    except:
        return None

for feat in layer.getFeatures():
    geom = feat.geometry()

    fs = normalize_speed(feat["fspeed_08"])
    bs = normalize_speed(feat["bspeed_08"])
    base_speed = normalize_speed(feat["speed_km_h"])

    # Если оба пустые — создаём два линка с speed_km_h
    if fs is None and bs is None and base_speed is not None:
        for oneway in ("T", "F"):
            f = QgsFeature(out_layer.fields())
            f.setGeometry(geom)
            f["ONEWAY"] = oneway
            f["MAXSPEED"] = float(base_speed)
            f["FCLASS"] = "service"
            prov.addFeature(f)
        continue

    # Прямое направление
    if fs is not None:
        f = QgsFeature(out_layer.fields())
        f.setGeometry(geom)
        f["ONEWAY"] = "T"
        f["MAXSPEED"] = float(fs)
        f["FCLASS"] = "service"
        prov.addFeature(f)

    # Обратное направление
    if bs is not None:
        b = QgsFeature(out_layer.fields())
        b.setGeometry(geom)
        b["ONEWAY"] = "F"
        b["MAXSPEED"] = float(bs)
        b["FCLASS"] = "service"
        prov.addFeature(b)

QgsProject.instance().addMapLayer(out_layer)
print("Готово!")
