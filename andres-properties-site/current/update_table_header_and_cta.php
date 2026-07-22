<?php
// 1) Renames the comparison table's "Feature" header to "The Difference".
// 2) Thickens/recolors the hero's "Call Jason Directly" button border from
//    a thin navy-ish hairline (1px #33395a) to a thicker copper border.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$table_widget_id = 'cmp0main';
$cta_widget_id = '2e2d70c';
$table_found = false;
$cta_found = false;

function walk(&$node, $table_widget_id, $cta_widget_id, &$table_found, &$cta_found) {
    if (!is_array($node)) return;
    if (isset($node['id'])) {
        if ($node['id'] === $table_widget_id && isset($node['settings']['html'])) {
            $before = $node['settings']['html'];
            $node['settings']['html'] = str_replace(
                '<th class="compare-th-feature">Feature</th>',
                '<th class="compare-th-feature">The Difference</th>',
                $node['settings']['html']
            );
            $table_found = ($node['settings']['html'] !== $before);
        }
        if ($node['id'] === $cta_widget_id && isset($node['settings']['html'])) {
            $before = $node['settings']['html'];
            $node['settings']['html'] = str_replace(
                'border:1px solid #33395a;',
                'border:2.5px solid #D1853F;',
                $node['settings']['html']
            );
            $cta_found = ($node['settings']['html'] !== $before);
        }
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk($child, $table_widget_id, $cta_widget_id, $table_found, $cta_found);
        }
    }
}

foreach ($data as &$section) {
    walk($section, $table_widget_id, $cta_widget_id, $table_found, $cta_found);
}

if (!$table_found) fwrite(STDERR, "Table header not updated (not found or no match).\n");
if (!$cta_found) fwrite(STDERR, "CTA border not updated (not found or no match).\n");
if (!$table_found || !$cta_found) exit(1);

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated table header and CTA border.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
