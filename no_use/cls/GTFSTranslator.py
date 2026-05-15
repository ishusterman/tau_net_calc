import pandas as pd
import os
from googletrans import Translator


class GTFSTranslator:
    def __init__(self, translations_path: str, input_dir: str, output_dir: str):
        self.translations_path = translations_path
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.translation_dict = self._load_translations()
        self.translator = Translator()

    # -----------------------------
    # 1. Load translations.txt
    # -----------------------------
    def _load_translations(self):
        tr = pd.read_csv(self.translations_path)
        tr_en = tr[tr["lang"] == "EN"]
        return dict(zip(tr_en["trans_id"], tr_en["translation"]))

    # -----------------------------
    # 2. Google Translate whole string
    # -----------------------------
    def _google_translate(self, text):
        try:
            return self.translator.translate(text, src="iw", dest="en").text
        except:
            return text

    # -----------------------------
    # 3. Translate stop_name (NO GOOGLE)
    # -----------------------------
    def _translate_stop_value(self, value):
        if pd.isna(value):
            return value
        value = value.strip()
        return self.translation_dict.get(value, value)

    # -----------------------------
    # 4. Translate route_long_name (WHOLE STRING)
    # -----------------------------
    def _translate_route_value(self, value):
        if pd.isna(value):
            return value

        value = value.strip()

        # 1) exact match in translations.txt
        if value in self.translation_dict:
            return self.translation_dict[value]

        # 2) translate whole string via Google
        return self._google_translate(value)

    # -----------------------------
    # 5. Translate agency_name (dictionary → Google)
    # -----------------------------
    def _translate_agency_value(self, value):
        if pd.isna(value):
            return value

        value = value.strip()

        if value in self.translation_dict:
            return self.translation_dict[value]

        return self._google_translate(value)

    # -----------------------------
    # 6. Generic file translator with progress
    # -----------------------------
    def _translate_file(self, filename: str, column: str, mode: str):
        path = os.path.join(self.input_dir, filename)
        if not os.path.exists(path):
            print(f"File {filename} not found, skipping")
            return

        df = pd.read_csv(path)
        total = len(df)

        print(f"Translating {filename} ({total} rows)")

        for i in range(total):
            value = df.at[i, column]

            if mode == "stops":
                df.at[i, column] = self._translate_stop_value(value)

            elif mode == "routes":
                df.at[i, column] = self._translate_route_value(value)

            elif mode == "agency":
                df.at[i, column] = self._translate_agency_value(value)

            if i % 100 == 0:
                percent = round(i / total * 100, 1)
                print(f"   {i}/{total} rows translated ({percent}%)")

        out_path = os.path.join(self.output_dir, filename.replace(".txt", "_en.txt"))
        df.to_csv(out_path, index=False)
        print(f"Finished {filename}")

    # -----------------------------
    # 7. Translate all GTFS files
    # -----------------------------
    def translate_all(self):
        self._translate_file("stops.txt", "stop_name", mode="stops")
        print("stop_name - ok")

        self._translate_file("routes.txt", "route_long_name", mode="routes")
        print("routes - ok")

        self._translate_file("agency.txt", "agency_name", mode="agency")
        print("agency - ok")

        print("Finish")


if __name__ == "__main__":

 translator = GTFSTranslator(
     translations_path=r"c:\doc\Igor\GIS\qgis-git-projects\GTFS2018\translations.txt",
     input_dir=r"c:\doc\Igor\GIS\qgis-git-projects\GTFS2018",
     output_dir=r"c:\doc\Igor\GIS\GTFS\ISR_2018_EN" )
 translator.translate_all()
