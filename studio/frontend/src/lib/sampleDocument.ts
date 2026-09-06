/**
 * The sample project from `studio/backend/tests/test_document.py::document`, as the
 * exact `model_dump(mode="json")` the backend would send (`?mock=1` loads it, so the
 * UI is developable and demoable with no backend running).
 *
 * It is annotated `ProjectDocument` rather than cast, so the mirror in `ir.ts` is
 * checked against a real payload every typecheck.
 */

import type { ProjectDocument } from "./ir";

export const SAMPLE_DOCUMENT: ProjectDocument = {
  "schema_version": 1,
  "revision": 12,
  "project": {
    "name": "Monitored estate",
    "package": "kg_project",
    "description": null,
    "data_directory": "data"
  },
  "annotation_types": [
    {
      "id": "provenance",
      "declaration_name": "Provenance",
      "namespace": "kg_project",
      "annotation_id": "provenance",
      "description": "Records which build stage produced or tracks a component.",
      "fields": [
        {
          "name": "stage",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null
        }
      ]
    }
  ],
  "structs": [
    {
      "id": "premises",
      "declaration_name": "PremisesStruct",
      "name": "premises",
      "description": null,
      "fields": [
        {
          "name": "contact_name",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "contact",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "struct",
              "module": "kg_project.table.sites",
              "qualname": "PremisesContactStruct"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "annotations": []
    },
    {
      "id": "premises_contact",
      "declaration_name": "PremisesContactStruct",
      "name": "premises_contact",
      "description": null,
      "fields": [
        {
          "name": "email",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "location",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "struct",
              "module": "kg_project.table.sites",
              "qualname": "PremisesContactLocationStruct"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "annotations": []
    },
    {
      "id": "premises_contact_location",
      "declaration_name": "PremisesContactLocationStruct",
      "name": "premises_contact_location",
      "description": null,
      "fields": [
        {
          "name": "city",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "room",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "annotations": []
    }
  ],
  "tables": [
    {
      "id": "sites",
      "declaration_name": "SitesTable",
      "name": "sites",
      "description": "One row per monitored site.",
      "fields": [
        {
          "name": "site_id",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "site_name",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "premises",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "struct",
              "module": "kg_project.table.sites",
              "qualname": "PremisesStruct"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "priority_scores",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "array",
              "item": {
                "kind": "nullable",
                "value": {
                  "kind": "unit",
                  "name": "int"
                }
              }
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "members": [],
      "annotations": [],
      "group": null
    },
    {
      "id": "equipment",
      "declaration_name": "EquipmentTable",
      "name": "equipment",
      "description": null,
      "fields": [
        {
          "name": "unit_ref",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "site_id",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "in_service",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "bool"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "survey_period",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "members": [],
      "annotations": [],
      "group": null
    },
    {
      "id": "readings",
      "declaration_name": "ReadingsTableGroup",
      "name": "readings",
      "description": null,
      "fields": [],
      "members": [
        {
          "python_name": "temperature",
          "ref": "temperature_readings"
        },
        {
          "python_name": "mechanical",
          "ref": "mechanical_readings"
        }
      ],
      "annotations": [],
      "group": null
    },
    {
      "id": "mechanical_readings",
      "declaration_name": "MechanicalTableGroup",
      "name": "mechanical",
      "description": null,
      "fields": [],
      "members": [
        {
          "python_name": "vibration",
          "ref": "vibration_readings"
        }
      ],
      "annotations": [],
      "group": "readings"
    },
    {
      "id": "temperature_readings",
      "declaration_name": "TemperatureTable",
      "name": "temperature",
      "description": null,
      "fields": [
        {
          "name": "unit_ref",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "deg_c",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "float"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "members": [
        {
          "python_name": "temperature",
          "ref": "temperature_readings"
        },
        {
          "python_name": "mechanical",
          "ref": "mechanical_readings"
        }
      ],
      "annotations": [],
      "group": "readings"
    },
    {
      "id": "vibration_readings",
      "declaration_name": "VibrationTable",
      "name": "vibration",
      "description": null,
      "fields": [
        {
          "name": "unit_ref",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "str"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        },
        {
          "name": "mm_s",
          "logical_type": {
            "kind": "nullable",
            "value": {
              "kind": "unit",
              "name": "float"
            }
          },
          "description": null,
          "external_name": null,
          "nullability": "defaulted",
          "schema_path": "",
          "annotations": []
        }
      ],
      "members": [
        {
          "python_name": "temperature",
          "ref": "temperature_readings"
        },
        {
          "python_name": "mechanical",
          "ref": "mechanical_readings"
        }
      ],
      "annotations": [],
      "group": "mechanical_readings"
    }
  ],
  "projections": [
    {
      "id": "site_cities",
      "declaration_name": "SiteCityProjection",
      "name": "site_cities",
      "description": null,
      "fields": [
        {
          "name": "site_id",
          "expression": {
            "kind": "field",
            "source": "sites",
            "path": [
              "site_id"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          },
          "description": null
        },
        {
          "name": "score",
          "expression": {
            "kind": "field",
            "source": "sites",
            "path": [
              "priority_scores"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "array",
                "item": {
                  "kind": "nullable",
                  "value": {
                    "kind": "unit",
                    "name": "int"
                  }
                }
              }
            }
          },
          "description": null
        }
      ],
      "annotations": []
    }
  ],
  "components": [
    {
      "id": "documented",
      "kind": "node",
      "tier": "category",
      "declaration_name": "DocumentedAbstractNode",
      "name": "documented",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": "Documented",
      "parent": null,
      "mixins": [],
      "source": null,
      "target": null,
      "properties": [
        {
          "name": "summary",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null,
          "optional": false,
          "annotations": []
        }
      ],
      "annotations": []
    },
    {
      "id": "provenanced_node",
      "kind": "node",
      "tier": "template",
      "declaration_name": "ProvenancedNodeTemplate",
      "name": "provenanced_node",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": null,
      "parent": null,
      "mixins": [],
      "source": null,
      "target": null,
      "properties": [
        {
          "name": "source_version",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null,
          "optional": false,
          "annotations": []
        }
      ],
      "annotations": [
        {
          "annotation_type": null,
          "import_module": "kg_project.annotations",
          "class_name": "Provenance",
          "arguments": {
            "stage": "built"
          }
        }
      ]
    },
    {
      "id": "site",
      "kind": "node",
      "tier": "concrete",
      "declaration_name": "SiteNode",
      "name": "site",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": "Site",
      "parent": "documented",
      "mixins": [
        "provenanced_node"
      ],
      "source": null,
      "target": null,
      "properties": [
        {
          "name": "name",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null,
          "optional": false,
          "annotations": []
        },
        {
          "name": "city",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null,
          "optional": false,
          "annotations": []
        }
      ],
      "annotations": []
    },
    {
      "id": "unit",
      "kind": "node",
      "tier": "concrete",
      "declaration_name": "UnitNode",
      "name": "unit",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": "Unit",
      "parent": "documented",
      "mixins": [
        "provenanced_node"
      ],
      "source": null,
      "target": null,
      "properties": [
        {
          "name": "name",
          "logical_type": {
            "kind": "unit",
            "name": "str"
          },
          "description": null,
          "optional": false,
          "annotations": []
        },
        {
          "name": "in_service",
          "logical_type": {
            "kind": "unit",
            "name": "bool"
          },
          "description": null,
          "optional": false,
          "annotations": []
        }
      ],
      "annotations": []
    },
    {
      "id": "monitored_relation",
      "kind": "edge",
      "tier": "category",
      "declaration_name": "MonitoredRelationAbstractEdge",
      "name": "monitored_relation",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": "MONITORED",
      "parent": null,
      "mixins": [],
      "source": "documented",
      "target": "documented",
      "properties": [],
      "annotations": []
    },
    {
      "id": "has_unit",
      "kind": "edge",
      "tier": "concrete",
      "declaration_name": "HasUnitEdge",
      "name": "has_unit",
      "description": "Category: every documented entity carries a human-readable summary.",
      "label": "HAS_UNIT",
      "parent": "monitored_relation",
      "mixins": [],
      "source": "site",
      "target": "unit",
      "properties": [],
      "annotations": []
    }
  ],
  "bindings": [
    {
      "id": "site_binding",
      "kind": "node",
      "component": "site",
      "debug_name": null,
      "build_key": {
        "kind": "operation",
        "operator": "where_present",
        "arguments": [
          {
            "kind": "field",
            "source": "sites",
            "path": [
              "site_id"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          }
        ],
        "parameters": {},
        "logical_type": {
          "kind": "unit",
          "name": "str"
        }
      },
      "source_build_key": null,
      "target_build_key": null,
      "source": null,
      "target": null,
      "properties": [
        {
          "name": "name",
          "expression": {
            "kind": "operation",
            "operator": "coalesce",
            "arguments": [
              {
                "kind": "field",
                "source": "sites",
                "path": [
                  "site_name"
                ],
                "logical_type": {
                  "kind": "nullable",
                  "value": {
                    "kind": "unit",
                    "name": "str"
                  }
                }
              },
              {
                "kind": "literal",
                "value": "Unnamed site",
                "logical_type": {
                  "kind": "unit",
                  "name": "str"
                }
              }
            ],
            "parameters": {},
            "logical_type": {
              "kind": "unit",
              "name": "str"
            }
          }
        },
        {
          "name": "city",
          "expression": {
            "kind": "field",
            "source": "sites",
            "path": [
              "premises",
              "contact",
              "location",
              "city"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          }
        }
      ],
      "annotations": []
    },
    {
      "id": "has_unit_binding",
      "kind": "edge",
      "component": "has_unit",
      "debug_name": null,
      "build_key": {
        "kind": "operation",
        "operator": "where_present",
        "arguments": [
          {
            "kind": "field",
            "source": "equipment",
            "path": [
              "unit_ref"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          }
        ],
        "parameters": {},
        "logical_type": {
          "kind": "unit",
          "name": "str"
        }
      },
      "source_build_key": {
        "kind": "operation",
        "operator": "where_present",
        "arguments": [
          {
            "kind": "field",
            "source": "equipment",
            "path": [
              "site_id"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          }
        ],
        "parameters": {},
        "logical_type": {
          "kind": "unit",
          "name": "str"
        }
      },
      "target_build_key": {
        "kind": "operation",
        "operator": "where_present",
        "arguments": [
          {
            "kind": "field",
            "source": "equipment",
            "path": [
              "unit_ref"
            ],
            "logical_type": {
              "kind": "nullable",
              "value": {
                "kind": "unit",
                "name": "str"
              }
            }
          }
        ],
        "parameters": {},
        "logical_type": {
          "kind": "unit",
          "name": "str"
        }
      },
      "source": null,
      "target": null,
      "properties": [],
      "annotations": []
    }
  ],
  "sources": [
    {
      "id": "sites_source",
      "table": "sites",
      "location": "data/sites.json",
      "format": "json",
      "layout": null,
      "version": "registry-2026-08",
      "credential_reference": null,
      "annotations": []
    },
    {
      "id": "equipment_source",
      "table": "equipment",
      "location": "data/equipment.json",
      "format": "json",
      "layout": null,
      "version": null,
      "credential_reference": null,
      "annotations": []
    },
    {
      "id": "readings_source",
      "table": "readings",
      "location": "data",
      "format": "json",
      "layout": "{group_path}/{table_name}.json",
      "version": null,
      "credential_reference": null,
      "annotations": []
    }
  ],
  "modules": [
    {
      "id": "collapse_exact_duplicates",
      "configuration": null,
      "enabled": true
    },
    {
      "id": "file",
      "configuration": {
        "relative_path": "graph.jsonl"
      },
      "enabled": true
    },
    {
      "id": "meta_graph",
      "configuration": null,
      "enabled": true
    }
  ],
  "views": {
    "topology": {
      "component:site": {
        "x": 120,
        "y": 80
      }
    }
  }
};
