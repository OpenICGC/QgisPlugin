<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyAlgorithm="0" minScale="1e+08" readOnly="0" maxScale="0" simplifyDrawingHints="0" version="3.4.6-Madeira" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0" simplifyDrawingTol="1" simplifyMaxScale="1" labelsEnabled="1" simplifyLocal="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 enableorderby="0" symbollevels="0" type="singleSymbol" forceraster="0">
    <symbols>
      <symbol type="marker" name="0" clip_to_extent="1" force_rhr="0" alpha="1">
        <layer class="SimpleMarker" locked="0" enabled="0" pass="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="183,72,75,255"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fontStrikeout="0" fontLetterSpacing="0" fontCapitals="0" fieldName="TEXT" fontSizeUnit="MapUnit" multilineHeight="1" useSubstitutions="0" fontSizeMapUnitScale="3x:0,0,0,0,0,0" isExpression="0" fontWeight="50" fontWordSpacing="0" blendMode="0" previewBkgrdColor="#ffffff" textColor="0,0,0,255" fontFamily="Times New Roman" textOpacity="1" namedStyle="Regular" fontSize="10" fontItalic="0" fontUnderline="0">
        <text-buffer bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferBlendMode="0" bufferSize="1" bufferColor="255,255,255,255" bufferNoFill="1" bufferJoinStyle="128" bufferDraw="0" bufferSizeUnits="MM" bufferOpacity="1"/>
        <background shapeFillColor="255,255,255,255" shapeType="0" shapeSizeUnit="MM" shapeBorderWidthUnit="MM" shapeBorderWidth="0" shapeSizeX="0" shapeBlendMode="0" shapeJoinStyle="64" shapeBorderColor="128,128,128,255" shapeOffsetY="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeDraw="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeRadiiX="0" shapeRadiiY="0" shapeSVGFile="" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetX="0" shapeRadiiUnit="MM" shapeOpacity="1" shapeRotationType="0" shapeSizeY="0" shapeOffsetUnit="MM" shapeRotation="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0"/>
        <shadow shadowOffsetAngle="135" shadowRadius="1.5" shadowOffsetDist="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOpacity="0.7" shadowDraw="0" shadowColor="0,0,0,255" shadowBlendMode="6" shadowRadiusUnit="MM" shadowOffsetGlobal="1" shadowUnder="0" shadowOffsetUnit="MM" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowScale="100"/>
        <substitutions/>
      </text-style>
      <text-format autoWrapLength="0" formatNumbers="0" addDirectionSymbol="0" decimals="3" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" plussign="0" rightDirectionSymbol=">" multilineAlign="3" wrapChar="" reverseDirectionSymbol="0" useMaxLineLengthForAutoWrap="1"/>
      <placement fitInPolygonOnly="0" maxCurvedCharAngleIn="25" repeatDistance="0" centroidWhole="0" offsetType="0" dist="0" rotationAngle="0" priority="5" repeatDistanceUnits="MM" quadOffset="0" preserveRotation="1" xOffset="0" placement="1" distUnits="MM" yOffset="0" offsetUnits="MM" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" maxCurvedCharAngleOut="-25" centroidInside="0" distMapUnitScale="3x:0,0,0,0,0,0" placementFlags="10" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0"/>
      <rendering mergeLines="0" minFeatureSize="0" obstacleType="0" scaleMin="0" fontMaxPixelSize="10000" limitNumLabels="0" labelPerPart="0" maxNumLabels="2000" fontMinPixelSize="3" zIndex="0" obstacleFactor="1" drawLabels="1" displayAll="1" fontLimitPixelSize="1" obstacle="1" upsidedownLabels="0" scaleMax="0" scaleVisibility="0"/>
      <dd_properties>
        <Option type="Map">
          <Option type="QString" name="name" value=""/>
          <Option type="Map" name="properties">
            <Option type="Map" name="Bold">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="&quot;BOLD&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="Color">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="if ( &quot;CAS&quot; like 'TOP_12%', '0,125,255','35,35,35')"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="Family">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="&quot;FONT&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="Italic">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="&quot;ITALIC&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="LabelRotation">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="360 - &quot;ROTATION&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="OffsetQuad">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="&quot;JT&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
            <Option type="Map" name="Size">
              <Option type="bool" name="active" value="true"/>
              <Option type="QString" name="expression" value="&quot;SIZE&quot;"/>
              <Option type="int" name="type" value="3"/>
            </Option>
          </Option>
          <Option type="QString" name="type" value="collection"/>
        </Option>
      </dd_properties>
    </settings>
  </labeling>
  <customproperties>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer attributeLegend="1" diagramType="Histogram">
    <DiagramCategory opacity="1" maxScaleDenominator="1e+08" penAlpha="255" labelPlacementMethod="XHeight" sizeType="MM" penWidth="0" penColor="#000000" rotationOffset="270" height="15" minimumSize="0" enabled="0" width="15" scaleBasedVisibility="0" backgroundColor="#ffffff" barWidth="5" scaleDependency="Area" lineSizeScale="3x:0,0,0,0,0,0" sizeScale="3x:0,0,0,0,0,0" minScaleDenominator="0" lineSizeType="MM" backgroundAlpha="255" diagramOrientation="Up">
      <fontProperties description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0" style=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings placement="0" priority="0" showAll="1" linePlacementFlags="18" zIndex="0" obstacle="0" dist="0">
    <properties>
      <Option type="Map">
        <Option type="QString" name="name" value=""/>
        <Option name="properties"/>
        <Option type="QString" name="type" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="CAS">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="TYPE">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="TEXT">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="FONT">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="BOLD">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ITALIC">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="JT">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="SIZE">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ROTATION">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="CAS" index="0"/>
    <alias name="" field="TYPE" index="1"/>
    <alias name="" field="TEXT" index="2"/>
    <alias name="" field="FONT" index="3"/>
    <alias name="" field="BOLD" index="4"/>
    <alias name="" field="ITALIC" index="5"/>
    <alias name="" field="JT" index="6"/>
    <alias name="" field="SIZE" index="7"/>
    <alias name="" field="ROTATION" index="8"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="CAS" expression="" applyOnUpdate="0"/>
    <default field="TYPE" expression="" applyOnUpdate="0"/>
    <default field="TEXT" expression="" applyOnUpdate="0"/>
    <default field="FONT" expression="" applyOnUpdate="0"/>
    <default field="BOLD" expression="" applyOnUpdate="0"/>
    <default field="ITALIC" expression="" applyOnUpdate="0"/>
    <default field="JT" expression="" applyOnUpdate="0"/>
    <default field="SIZE" expression="" applyOnUpdate="0"/>
    <default field="ROTATION" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint notnull_strength="0" field="CAS" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="TYPE" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="TEXT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="FONT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="BOLD" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ITALIC" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="JT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="SIZE" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ROTATION" constraints="0" unique_strength="0" exp_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="CAS" exp="" desc=""/>
    <constraint field="TYPE" exp="" desc=""/>
    <constraint field="TEXT" exp="" desc=""/>
    <constraint field="FONT" exp="" desc=""/>
    <constraint field="BOLD" exp="" desc=""/>
    <constraint field="ITALIC" exp="" desc=""/>
    <constraint field="JT" exp="" desc=""/>
    <constraint field="SIZE" exp="" desc=""/>
    <constraint field="ROTATION" exp="" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortExpression="" actionWidgetStyle="dropDown" sortOrder="0">
    <columns>
      <column type="field" name="CAS" hidden="0" width="-1"/>
      <column type="field" name="TYPE" hidden="0" width="-1"/>
      <column type="field" name="TEXT" hidden="0" width="-1"/>
      <column type="field" name="FONT" hidden="0" width="-1"/>
      <column type="field" name="BOLD" hidden="0" width="-1"/>
      <column type="field" name="ITALIC" hidden="0" width="-1"/>
      <column type="field" name="JT" hidden="0" width="-1"/>
      <column type="field" name="SIZE" hidden="0" width="-1"/>
      <column type="field" name="ROTATION" hidden="0" width="-1"/>
      <column type="actions" hidden="1" width="-1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
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
    <field editable="1" name="BOLD"/>
    <field editable="1" name="CAS"/>
    <field editable="1" name="FONT"/>
    <field editable="1" name="ITALIC"/>
    <field editable="1" name="JT"/>
    <field editable="1" name="ROTATION"/>
    <field editable="1" name="SIZE"/>
    <field editable="1" name="TEXT"/>
    <field editable="1" name="TYPE"/>
  </editable>
  <labelOnTop>
    <field name="BOLD" labelOnTop="0"/>
    <field name="CAS" labelOnTop="0"/>
    <field name="FONT" labelOnTop="0"/>
    <field name="ITALIC" labelOnTop="0"/>
    <field name="JT" labelOnTop="0"/>
    <field name="ROTATION" labelOnTop="0"/>
    <field name="SIZE" labelOnTop="0"/>
    <field name="TEXT" labelOnTop="0"/>
    <field name="TYPE" labelOnTop="0"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>CAS</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
