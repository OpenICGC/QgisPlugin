<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyAlgorithm="0" version="3.10.6-A Coruña" readOnly="0" simplifyMaxScale="1" hasScaleBasedVisibilityFlag="0" styleCategories="AllStyleCategories" simplifyDrawingTol="1" minScale="0" simplifyLocal="1" maxScale="0" labelsEnabled="1" simplifyDrawingHints="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 enableorderby="0" forceraster="0" type="singleSymbol" symbollevels="0">
    <symbols>
      <symbol name="0" force_rhr="0" type="fill" alpha="1" clip_to_extent="1">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="164,113,88,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,255,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.6" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="no" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style isExpression="1" fontUnderline="0" textOpacity="1" namedStyle="Regular" textOrientation="horizontal" blendMode="0" fontItalic="0" fontWeight="50" fontWordSpacing="0" fontLetterSpacing="0" fontFamily="MS Shell Dlg 2" fieldName="case&#xd;&#xa;&#x9;when @layer_id  like '%talllidar%' then   substr( &quot;IDABS&quot; ,0,3)  || '-' ||   substr( &quot;IDABS&quot; ,4,3) &#xd;&#xa;&#x9;when @layer_id  like '%tall100m%' then  attribute('ID100MABS')&#xd;&#xa;&#x9;else  &quot;IDVISABS&quot; ||  ' (' ||   &quot;IDVISREL&quot;  || ')'&#xd;&#xa;end" fontSizeUnit="Point" fontCapitals="0" fontStrikeout="0" textColor="0,0,255,255" useSubstitutions="1" fontKerning="1" multilineHeight="1" previewBkgrdColor="255,255,255,255" fontSize="10" fontSizeMapUnitScale="3x:0,0,0,0,0,0">
        <text-buffer bufferSize="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferBlendMode="0" bufferOpacity="1" bufferColor="255,255,255,255" bufferNoFill="1" bufferJoinStyle="128" bufferSizeUnits="MM" bufferDraw="0"/>
        <background shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeJoinStyle="64" shapeOffsetX="0" shapeSizeY="0" shapeOffsetY="0" shapeType="0" shapeDraw="0" shapeSizeX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeRadiiY="0" shapeOffsetUnit="MM" shapeRotation="0" shapeOpacity="1" shapeRadiiX="0" shapeRadiiUnit="MM" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeUnit="MM" shapeSizeType="0" shapeBlendMode="0" shapeRotationType="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeFillColor="255,255,255,255" shapeBorderWidth="0">
          <symbol name="markerSymbol" force_rhr="0" type="marker" alpha="1" clip_to_extent="1">
            <layer class="SimpleMarker" enabled="1" pass="0" locked="0">
              <prop v="0" k="angle"/>
              <prop v="243,166,178,255" k="color"/>
              <prop v="1" k="horizontal_anchor_point"/>
              <prop v="bevel" k="joinstyle"/>
              <prop v="circle" k="name"/>
              <prop v="0,0" k="offset"/>
              <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
              <prop v="MM" k="offset_unit"/>
              <prop v="35,35,35,255" k="outline_color"/>
              <prop v="solid" k="outline_style"/>
              <prop v="0" k="outline_width"/>
              <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
              <prop v="MM" k="outline_width_unit"/>
              <prop v="diameter" k="scale_method"/>
              <prop v="2" k="size"/>
              <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
              <prop v="MM" k="size_unit"/>
              <prop v="1" k="vertical_anchor_point"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" value="" type="QString"/>
                  <Option name="properties"/>
                  <Option name="type" value="collection" type="QString"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </background>
        <shadow shadowOffsetUnit="MM" shadowRadiusUnit="MM" shadowOpacity="0.7" shadowColor="0,0,0,255" shadowDraw="0" shadowUnder="0" shadowOffsetDist="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetGlobal="1" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowBlendMode="6" shadowRadius="1.5" shadowScale="100" shadowOffsetAngle="135" shadowRadiusAlphaOnly="0"/>
        <dd_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </dd_properties>
        <substitutions/>
      </text-style>
      <text-format multilineAlign="1" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" reverseDirectionSymbol="0" rightDirectionSymbol=">" useMaxLineLengthForAutoWrap="1" formatNumbers="0" addDirectionSymbol="0" plussign="0" wrapChar=" " decimals="3" autoWrapLength="0"/>
      <placement offsetUnits="MM" placement="1" geometryGeneratorType="PointGeometry" xOffset="0" distUnits="MM" centroidWhole="0" dist="0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" rotationAngle="0" priority="5" yOffset="0" maxCurvedCharAngleIn="25" placementFlags="10" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" overrunDistance="0" layerType="PolygonGeometry" centroidInside="0" repeatDistance="0" repeatDistanceUnits="MM" fitInPolygonOnly="1" distMapUnitScale="3x:0,0,0,0,0,0" geometryGenerator="" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" maxCurvedCharAngleOut="-25" geometryGeneratorEnabled="0" offsetType="0" preserveRotation="1" overrunDistanceUnit="MM" quadOffset="4"/>
      <rendering scaleMax="200000" maxNumLabels="2000" obstacleType="0" fontLimitPixelSize="0" scaleMin="0" zIndex="0" upsidedownLabels="0" labelPerPart="0" fontMinPixelSize="3" minFeatureSize="0" fontMaxPixelSize="10000" limitNumLabels="0" displayAll="0" obstacle="1" mergeLines="0" drawLabels="1" obstacleFactor="1" scaleVisibility="1"/>
      <dd_properties>
        <Option type="Map">
          <Option name="name" value="" type="QString"/>
          <Option name="properties" type="Map">
            <Option name="MinimumScale" type="Map">
              <Option name="active" value="true" type="bool"/>
              <Option name="expression" value="case&#xd;&#xa;&#x9;when @layer_id  like '%talllidar%' then 100000&#xd;&#xa;&#x9;when @layer_id  like '%tall5m%' then 200000&#xd;&#xa;&#x9;when @layer_id  like '%tall10m%' then 500000&#xd;&#xa;&#x9;when @layer_id  like '%tall25m%' then 1000000&#xd;&#xa;&#x9;else 2000000&#xd;&#xa;end" type="QString"/>
              <Option name="type" value="3" type="int"/>
            </Option>
          </Option>
          <Option name="type" value="collection" type="QString"/>
        </Option>
      </dd_properties>
      <callout type="simple">
        <Option type="Map">
          <Option name="anchorPoint" value="pole_of_inaccessibility" type="QString"/>
          <Option name="ddProperties" type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
          <Option name="drawToAllParts" value="false" type="bool"/>
          <Option name="enabled" value="0" type="QString"/>
          <Option name="lineSymbol" value="&lt;symbol name=&quot;symbol&quot; force_rhr=&quot;0&quot; type=&quot;line&quot; alpha=&quot;1&quot; clip_to_extent=&quot;1&quot;>&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; pass=&quot;0&quot; locked=&quot;0&quot;>&lt;prop v=&quot;square&quot; k=&quot;capstyle&quot;/>&lt;prop v=&quot;5;2&quot; k=&quot;customdash&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;customdash_map_unit_scale&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;customdash_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;draw_inside_polygon&quot;/>&lt;prop v=&quot;bevel&quot; k=&quot;joinstyle&quot;/>&lt;prop v=&quot;60,60,60,255&quot; k=&quot;line_color&quot;/>&lt;prop v=&quot;solid&quot; k=&quot;line_style&quot;/>&lt;prop v=&quot;0.3&quot; k=&quot;line_width&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;line_width_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;offset&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;offset_map_unit_scale&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;offset_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;ring_filter&quot;/>&lt;prop v=&quot;0&quot; k=&quot;use_custom_dash&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;width_map_unit_scale&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option name=&quot;name&quot; value=&quot;&quot; type=&quot;QString&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option name=&quot;type&quot; value=&quot;collection&quot; type=&quot;QString&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" type="QString"/>
          <Option name="minLength" value="0" type="double"/>
          <Option name="minLengthMapUnitScale" value="3x:0,0,0,0,0,0" type="QString"/>
          <Option name="minLengthUnit" value="MM" type="QString"/>
          <Option name="offsetFromAnchor" value="0" type="double"/>
          <Option name="offsetFromAnchorMapUnitScale" value="3x:0,0,0,0,0,0" type="QString"/>
          <Option name="offsetFromAnchorUnit" value="MM" type="QString"/>
          <Option name="offsetFromLabel" value="0" type="double"/>
          <Option name="offsetFromLabelMapUnitScale" value="3x:0,0,0,0,0,0" type="QString"/>
          <Option name="offsetFromLabelUnit" value="MM" type="QString"/>
        </Option>
      </callout>
    </settings>
  </labeling>
  <customproperties>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory width="15" enabled="0" rotationOffset="270" opacity="1" height="15" labelPlacementMethod="XHeight" backgroundAlpha="255" penColor="#000000" minimumSize="0" backgroundColor="#ffffff" diagramOrientation="Up" scaleDependency="Area" penAlpha="255" sizeScale="3x:0,0,0,0,0,0" sizeType="MM" barWidth="5" lineSizeType="MM" lineSizeScale="3x:0,0,0,0,0,0" minScaleDenominator="0" penWidth="0" maxScaleDenominator="1e+08" scaleBasedVisibility="0">
      <fontProperties description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0" style=""/>
      <attribute field="" color="#000000" label=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings linePlacementFlags="18" showAll="1" zIndex="0" placement="1" priority="0" obstacle="0" dist="0">
    <properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration type="Map">
      <Option name="QgsGeometryGapCheck" type="Map">
        <Option name="allowedGapsBuffer" value="0" type="double"/>
        <Option name="allowedGapsEnabled" value="false" type="bool"/>
        <Option name="allowedGapsLayer" value="" type="QString"/>
      </Option>
    </checkConfiguration>
  </geometryOptions>
  <fieldConfiguration>
    <field name="IDVISREL">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="COLABS">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="IDVISABS">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ID50M">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="IDABS">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="FILABS">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="IDVISREL" index="0"/>
    <alias name="" field="COLABS" index="1"/>
    <alias name="" field="IDVISABS" index="2"/>
    <alias name="" field="ID50M" index="3"/>
    <alias name="" field="IDABS" index="4"/>
    <alias name="" field="FILABS" index="5"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default expression="" field="IDVISREL" applyOnUpdate="0"/>
    <default expression="" field="COLABS" applyOnUpdate="0"/>
    <default expression="" field="IDVISABS" applyOnUpdate="0"/>
    <default expression="" field="ID50M" applyOnUpdate="0"/>
    <default expression="" field="IDABS" applyOnUpdate="0"/>
    <default expression="" field="FILABS" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint field="IDVISREL" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
    <constraint field="COLABS" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
    <constraint field="IDVISABS" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
    <constraint field="ID50M" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
    <constraint field="IDABS" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
    <constraint field="FILABS" constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="IDVISREL" exp="" desc=""/>
    <constraint field="COLABS" exp="" desc=""/>
    <constraint field="IDVISABS" exp="" desc=""/>
    <constraint field="ID50M" exp="" desc=""/>
    <constraint field="IDABS" exp="" desc=""/>
    <constraint field="FILABS" exp="" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" actionWidgetStyle="dropDown" sortExpression="">
    <columns>
      <column name="IDABS" hidden="0" type="field" width="-1"/>
      <column hidden="1" type="actions" width="-1"/>
      <column name="IDVISREL" hidden="0" type="field" width="-1"/>
      <column name="COLABS" hidden="0" type="field" width="-1"/>
      <column name="IDVISABS" hidden="0" type="field" width="-1"/>
      <column name="ID50M" hidden="0" type="field" width="-1"/>
      <column name="FILABS" hidden="0" type="field" width="-1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="COLABS" editable="1"/>
    <field name="COLREL" editable="1"/>
    <field name="FILABS" editable="1"/>
    <field name="FILREL" editable="1"/>
    <field name="ID50M" editable="1"/>
    <field name="IDABS" editable="1"/>
    <field name="IDREL" editable="1"/>
    <field name="IDVISABS" editable="1"/>
    <field name="IDVISREL" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="COLABS" labelOnTop="0"/>
    <field name="COLREL" labelOnTop="0"/>
    <field name="FILABS" labelOnTop="0"/>
    <field name="FILREL" labelOnTop="0"/>
    <field name="ID50M" labelOnTop="0"/>
    <field name="IDABS" labelOnTop="0"/>
    <field name="IDREL" labelOnTop="0"/>
    <field name="IDVISABS" labelOnTop="0"/>
    <field name="IDVISREL" labelOnTop="0"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>IDABS</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
