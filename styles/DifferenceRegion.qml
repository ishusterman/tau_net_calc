<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44" styleCategories="Symbology">

  <renderer-v2 type="graduatedSymbol" graduatedMethod="GraduatedColor" attr="__FIELD__">

    <!-- Базовый символ -->
    <source-symbol>
      <symbol type="fill" name="source" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="255,255,255,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>
    </source-symbol>

    <!-- Цвета классов -->
    <symbols>

      <symbol type="fill" name="0" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="148,185,0,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

      <symbol type="fill" name="1" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="134,204,127,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

      <symbol type="fill" name="2" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="62,165,90,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

      <symbol type="fill" name="3" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="33,144,72,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

      <symbol type="fill" name="4" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="15,106,53,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

      <symbol type="fill" name="5" clip_to_extent="1" alpha="1">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <Option name="color" value="0,63,33,255"/>
          <Option name="outline_color" value="35,35,35,0"/>
          <Option name="outline_width" value="0"/>
        </layer>
      </symbol>

    </symbols>

    <!-- Заглушки диапазонов -->
    <ranges>
      <range symbol="0" render="true" label="LOW1 – UP1" lower="LOW1" upper="UP1"/>
      <range symbol="1" render="true" label="LOW2 – UP2" lower="LOW2" upper="UP2"/>
      <range symbol="2" render="true" label="LOW3 – UP3" lower="LOW3" upper="UP3"/>
      <range symbol="3" render="true" label="LOW4 – UP4" lower="LOW4" upper="UP4"/>
      <range symbol="4" render="true" label="LOW5 – UP5" lower="LOW5" upper="UP5"/>
      <range symbol="5" render="true" label="LOW6 – UP6" lower="LOW6" upper="UP6"/>
    </ranges>

    <classificationMethod id="Quantile">
      <labelFormat format="%1 – %2" labelprecision="1"/>
    </classificationMethod>

  </renderer-v2>

</qgis>
