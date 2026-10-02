# H1 v2 test results (aggregates only)

Rows are listed in no rank order. Author reference baselines run the FindingFrame linker, which is not distributed here; they are context, not entries. Category F1 and Entity F1 are never combined.

400 test worlds, 50 per family. Overall rows: equal-world means with a world bootstrap (seed 42, 10,000 draws); family rows: the same bootstrap inside one family; contrasts: paired bootstrap resampling worlds within each family, equal-family mean. Category F1 and Entity F1 are reported separately and never combined. A world with no answer scores as unresolved singletons and stays in the denominator.

## Overall

| system | kind | answered | Category F1 [95% CI] | Entity F1 [95% CI] | cat split | cat merge | ent split | ent merge |
|---|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | LLM, one pass per world, temperature 0, paper prompt | 400/400 | 0.925 [0.911, 0.938] | 0.888 [0.876, 0.900] | 0.142 | 0.000 | 0.170 | 0.088 |
| GLM 5.3 flash | LLM, one pass per world, temperature 0, paper prompt | 342/400 | 0.850 [0.825, 0.873] | 0.817 [0.794, 0.839] | 0.245 | 0.000 | 0.254 | 0.089 |
| one_group_per_world | public baseline (h1bench, no FindingFrame code) | 400/400 | 0.676 [0.669, 0.682] | 0.599 [0.590, 0.608] | 0.000 | 0.539 | 0.000 | 0.628 |
| one_group_per_mention | public baseline (h1bench, no FindingFrame code) | 400/400 | 0.344 [0.340, 0.348] | 0.392 [0.385, 0.398] | 1.000 | 0.000 | 1.000 | 0.000 |
| raw_surface_equality | public baseline (h1bench, no FindingFrame code) | 400/400 | 0.603 [0.594, 0.612] | 0.575 [0.567, 0.584] | 0.547 | 0.437 | 0.553 | 0.568 |
| exact_normalized_key | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.920 [0.906, 0.933] | 0.847 [0.835, 0.860] | 0.151 | 0.000 | 0.151 | 0.176 |
| current_compatibility_linker | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.947 [0.933, 0.960] | 0.874 [0.860, 0.888] | 0.093 | 0.000 | 0.093 | 0.176 |
| descriptor_exact_normalized_key_v1 | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.909 [0.895, 0.922] | 0.858 [0.845, 0.871] | 0.177 | 0.000 | 0.151 | 0.150 |
| no_anatomy_hierarchy | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.913 [0.898, 0.928] | 0.841 [0.827, 0.854] | 0.151 | 0.043 | 0.151 | 0.219 |
| strict_laterality | author reference baseline (FindingFrame linker, unranked) | 400/400 | 1.000 [1.000, 1.000] | 0.927 [0.918, 0.937] | 0.000 | 0.000 | 0.000 | 0.176 |
| raw_anatomy | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.913 [0.898, 0.928] | 0.841 [0.827, 0.854] | 0.151 | 0.043 | 0.151 | 0.219 |
| descriptor_removed | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.920 [0.906, 0.933] | 0.847 [0.835, 0.860] | 0.151 | 0.000 | 0.151 | 0.176 |
| input_report_order_reversed | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.947 [0.933, 0.960] | 0.874 [0.860, 0.888] | 0.093 | 0.000 | 0.093 | 0.176 |
| tied_event_order_reversed | author reference baseline (FindingFrame linker, unranked) | 400/400 | 0.947 [0.933, 0.960] | 0.874 [0.860, 0.888] | 0.093 | 0.000 | 0.093 | 0.176 |
| oracle_ceiling_scorer_only | scorer ceiling (labels as predictions; not a system) | 400/400 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 | 0.000 | 0.000 | 0.000 |

## Per family: Category F1 (mean [95% CI], 50 worlds each)

| system | descriptor_pair_with_distractor | episode_reuse_with_distractor | granularity_with_laterality_distractor | granularity_with_organ_distractor | laterality_pair_same_type | same_site_different_type | same_word_different_organ | simultaneous_distinct_with_distractor |
|---|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.699 [0.680, 0.724] | 0.698 [0.679, 0.724] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| GLM 5.3 flash | 1.000 [1.000, 1.000] | 0.961 [0.909, 1.000] | 0.554 [0.506, 0.601] | 0.565 [0.518, 0.610] | 0.878 [0.797, 0.946] | 0.852 [0.771, 0.921] | 1.000 [1.000, 1.000] | 0.986 [0.958, 1.000] |
| one_group_per_world | 0.718 [0.712, 0.725] | 0.698 [0.693, 0.703] | 0.694 [0.688, 0.701] | 0.691 [0.686, 0.696] | 0.686 [0.680, 0.692] | 0.694 [0.687, 0.700] | 0.509 [0.507, 0.511] | 0.715 [0.709, 0.722] |
| one_group_per_mention | 0.323 [0.315, 0.331] | 0.352 [0.343, 0.361] | 0.337 [0.328, 0.346] | 0.333 [0.324, 0.343] | 0.330 [0.323, 0.337] | 0.338 [0.329, 0.347] | 0.414 [0.406, 0.421] | 0.324 [0.315, 0.332] |
| raw_surface_equality | 0.679 [0.662, 0.696] | 0.675 [0.655, 0.699] | 0.588 [0.570, 0.608] | 0.581 [0.563, 0.602] | 0.512 [0.496, 0.528] | 0.621 [0.601, 0.643] | 0.499 [0.481, 0.518] | 0.667 [0.651, 0.683] |
| exact_normalized_key | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| current_compatibility_linker | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.584] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| descriptor_exact_normalized_key_v1 | 0.912 [0.884, 0.940] | 1.000 [1.000, 1.000] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| no_anatomy_hierarchy | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.680 [0.678, 0.682] | 0.625 [0.622, 0.630] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| strict_laterality | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| raw_anatomy | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.680 [0.678, 0.682] | 0.625 [0.622, 0.630] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| descriptor_removed | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| input_report_order_reversed | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.584] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| tied_event_order_reversed | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.584] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| oracle_ceiling_scorer_only | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

## Per family: Entity F1 (mean [95% CI], 50 worlds each)

| system | descriptor_pair_with_distractor | episode_reuse_with_distractor | granularity_with_laterality_distractor | granularity_with_organ_distractor | laterality_pair_same_type | same_site_different_type | same_word_different_organ | simultaneous_distinct_with_distractor |
|---|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | 0.882 [0.850, 0.914] | 0.974 [0.960, 0.988] | 0.927 [0.897, 0.955] | 0.797 [0.756, 0.838] | 0.872 [0.836, 0.905] | 0.864 [0.833, 0.895] | 1.000 [1.000, 1.000] | 0.787 [0.771, 0.804] |
| GLM 5.3 flash | 0.880 [0.852, 0.910] | 0.957 [0.919, 0.987] | 0.707 [0.625, 0.789] | 0.610 [0.547, 0.673] | 0.808 [0.736, 0.874] | 0.793 [0.719, 0.861] | 1.000 [1.000, 1.000] | 0.782 [0.759, 0.803] |
| one_group_per_world | 0.503 [0.502, 0.504] | 0.511 [0.509, 0.513] | 0.694 [0.688, 0.701] | 0.691 [0.686, 0.696] | 0.686 [0.680, 0.692] | 0.694 [0.687, 0.700] | 0.509 [0.507, 0.511] | 0.503 [0.502, 0.504] |
| one_group_per_mention | 0.448 [0.437, 0.458] | 0.485 [0.474, 0.497] | 0.337 [0.328, 0.346] | 0.333 [0.324, 0.343] | 0.330 [0.323, 0.337] | 0.338 [0.329, 0.347] | 0.414 [0.406, 0.421] | 0.449 [0.439, 0.460] |
| raw_surface_equality | 0.591 [0.570, 0.614] | 0.612 [0.589, 0.638] | 0.588 [0.569, 0.608] | 0.581 [0.563, 0.601] | 0.512 [0.496, 0.529] | 0.621 [0.602, 0.643] | 0.499 [0.481, 0.518] | 0.595 [0.574, 0.620] |
| exact_normalized_key | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| current_compatibility_linker | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.585] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| descriptor_exact_normalized_key_v1 | 0.887 [0.859, 0.916] | 0.819 [0.815, 0.824] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| no_anatomy_hierarchy | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 0.680 [0.678, 0.682] | 0.625 [0.621, 0.630] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| strict_laterality | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| raw_anatomy | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 0.680 [0.678, 0.682] | 0.625 [0.621, 0.630] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| descriptor_removed | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 0.680 [0.678, 0.682] | 0.679 [0.677, 0.681] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| input_report_order_reversed | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.585] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| tied_event_order_reversed | 0.799 [0.794, 0.804] | 0.819 [0.815, 0.824] | 1.000 [1.000, 1.000] | 0.574 [0.565, 0.585] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.801 [0.797, 0.805] |
| oracle_ceiling_scorer_only | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

## Per family: split and merge pair rates (means)

| system | partition | rate | descriptor_pair_with_distractor | episode_reuse_with_distractor | granularity_with_laterality_distractor | granularity_with_organ_distractor | laterality_pair_same_type | same_site_different_type | same_word_different_organ | simultaneous_distinct_with_distractor |
|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | category | split | 0.000 | 0.000 | 0.566 | 0.566 | 0.000 | 0.000 | 0.000 | 0.000 |
| DeepSeek v4.1 flash | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| DeepSeek v4.1 flash | entity | split | 0.041 | 0.069 | 0.166 | 0.392 | 0.281 | 0.310 | 0.000 | 0.102 |
| DeepSeek v4.1 flash | entity | merge | 0.255 | 0.000 | 0.000 | 0.007 | 0.000 | 0.000 | 0.000 | 0.438 |
| GLM 5.3 flash | category | split | 0.000 | 0.060 | 0.746 | 0.732 | 0.180 | 0.220 | 0.000 | 0.020 |
| GLM 5.3 flash | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| GLM 5.3 flash | entity | split | 0.013 | 0.091 | 0.466 | 0.650 | 0.338 | 0.366 | 0.000 | 0.107 |
| GLM 5.3 flash | entity | merge | 0.275 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.433 |
| one_group_per_world | category | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| one_group_per_world | category | merge | 0.486 | 0.520 | 0.521 | 0.525 | 0.530 | 0.522 | 0.721 | 0.490 |
| one_group_per_world | entity | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| one_group_per_world | entity | merge | 0.735 | 0.735 | 0.521 | 0.525 | 0.530 | 0.522 | 0.721 | 0.735 |
| one_group_per_mention | category | split | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| one_group_per_mention | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| one_group_per_mention | entity | split | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| one_group_per_mention | entity | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_surface_equality | category | split | 0.500 | 0.509 | 0.508 | 0.512 | 0.688 | 0.639 | 0.491 | 0.527 |
| raw_surface_equality | category | merge | 0.286 | 0.335 | 0.526 | 0.532 | 0.555 | 0.317 | 0.718 | 0.227 |
| raw_surface_equality | entity | split | 0.511 | 0.513 | 0.508 | 0.512 | 0.688 | 0.639 | 0.491 | 0.563 |
| raw_surface_equality | entity | merge | 0.637 | 0.637 | 0.526 | 0.532 | 0.555 | 0.317 | 0.718 | 0.625 |
| exact_normalized_key | category | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| exact_normalized_key | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| exact_normalized_key | entity | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| exact_normalized_key | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| current_compatibility_linker | category | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| current_compatibility_linker | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| current_compatibility_linker | entity | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| current_compatibility_linker | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| descriptor_exact_normalized_key_v1 | category | split | 0.210 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_exact_normalized_key_v1 | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_exact_normalized_key_v1 | entity | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_exact_normalized_key_v1 | entity | merge | 0.271 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| no_anatomy_hierarchy | category | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_anatomy_hierarchy | category | merge | 0.000 | 0.000 | 0.000 | 0.341 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_anatomy_hierarchy | entity | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_anatomy_hierarchy | entity | merge | 0.482 | 0.447 | 0.000 | 0.341 | 0.000 | 0.000 | 0.000 | 0.479 |
| strict_laterality | category | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| strict_laterality | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| strict_laterality | entity | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| strict_laterality | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| raw_anatomy | category | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_anatomy | category | merge | 0.000 | 0.000 | 0.000 | 0.341 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_anatomy | entity | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_anatomy | entity | merge | 0.482 | 0.447 | 0.000 | 0.341 | 0.000 | 0.000 | 0.000 | 0.479 |
| descriptor_removed | category | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_removed | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_removed | entity | split | 0.000 | 0.000 | 0.602 | 0.603 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_removed | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| input_report_order_reversed | category | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| input_report_order_reversed | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| input_report_order_reversed | entity | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| input_report_order_reversed | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| tied_event_order_reversed | category | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| tied_event_order_reversed | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| tied_event_order_reversed | entity | split | 0.000 | 0.000 | 0.000 | 0.747 | 0.000 | 0.000 | 0.000 | 0.000 |
| tied_event_order_reversed | entity | merge | 0.482 | 0.447 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.479 |
| oracle_ceiling_scorer_only | category | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| oracle_ceiling_scorer_only | category | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| oracle_ceiling_scorer_only | entity | split | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| oracle_ceiling_scorer_only | entity | merge | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Unresolved mention rate (mean over worlds)

| system | ALL | descriptor_pair_with_distractor | episode_reuse_with_distractor | granularity_with_laterality_distractor | granularity_with_organ_distractor | laterality_pair_same_type | same_site_different_type | same_word_different_organ | simultaneous_distinct_with_distractor |
|---|---|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| GLM 5.3 flash | 0.145 | 0.000 | 0.060 | 0.360 | 0.320 | 0.180 | 0.220 | 0.000 | 0.020 |
| one_group_per_world | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| one_group_per_mention | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_surface_equality | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| exact_normalized_key | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| current_compatibility_linker | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_exact_normalized_key_v1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_anatomy_hierarchy | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| strict_laterality | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_anatomy | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| descriptor_removed | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| input_report_order_reversed | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| tied_event_order_reversed | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| oracle_ceiling_scorer_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
