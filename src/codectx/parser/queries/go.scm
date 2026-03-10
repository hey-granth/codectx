; Go import and symbol queries
(import_declaration) @import
(import_spec) @import
(function_declaration name: (identifier) @name) @function
(method_declaration name: (field_identifier) @name) @method
(type_declaration (type_spec name: (type_identifier) @name)) @class
