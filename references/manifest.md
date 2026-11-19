# Manifest and evidence

Use the original [example](../examples/bracket.json) as a starting point. The top-level fields are `version: 1`, `units: "mm"`, `title`, `drawing_id`, `layers`, `entities`, and `requirements`. Optional fields are `font`, `tolerance_mm`, `sheet` and `required_formats`. Model coordinates are WCS millimetres. A layer declares ACI `color`, `weight` in hundredths of a millimetre and `linetype` of CONTINUOUS, CENTER or DASHED.

| Entity type | Parameters besides id, layer and source |
|---|---|
| line | start, end |
| circle | center, radius |
| arc | center, radius, start_angle, end_angle in degrees, CCW |
| polyline | points, optional closed. Do not duplicate the first vertex at the end |
| text | insert, height, text |
| linear_dimension | start, end, base, expected measured value, optional angle in degrees |

Each entity has a stable `id` stored as DXF XDATA. Existing native handles are not relied on for generated documents. Every `source` should identify a source sheet, note, table cell or derivation. For calibrated approximations mention the calibration and limits, and avoid making unsupported model geometry appear exact.

Each requirement declares an `id`, `statement`, `source`, `scope` and optionally `entities` and `visual: true`. Use `required`, `optional`, `undecided` or `excluded`. Undecided and excluded both require a `decision` field. An unresolved scope blocks release. An excluded item should record who confirmed the decision or where the scope was stated. A result without a linked entity requires independent review evidence. Use a distinct entry for a section marker and each requested section sheet.

The sheet uses `size_mm`, `left_margin`, `edge_margin`, `scale_denominator`, `view_center` and optional `architectural_ticks`. The generated reference layout has a single locked viewport and a basic title block. Institutions may require a different block. Confirm installed font availability, printable bounds and plotting device media.

A revision JSON uses the following structure. `move` accepts a two-element `delta`. `set_text` accepts `value`. Geometric moves in a dimensioned drawing need explicit remapping and are outside the patch API. Other modifications require a reviewed CAD copy or manifest update.

```json
{"input_sha256":"<fingerprint>","operations":[
  {"op":"set_text","id":"description","value":"复核完成","reason":"Confirmed wording change"}
]}
```

Visual evidence is supplied separately after examination. For each reviewed requirement, copy the complete hash map printed in the associated audit report into `sha256` and describe the inspection in `note`. New or broken hashes invalidate the review. This is an evidence record, not a digital signature.
