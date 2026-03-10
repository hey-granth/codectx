; Rust import and symbol queries
(use_declaration) @import
(function_item name: (identifier) @name) @function
(struct_item name: (type_identifier) @name) @class
(enum_item name: (type_identifier) @name) @class
(impl_item) @class
(trait_item name: (type_identifier) @name) @class
