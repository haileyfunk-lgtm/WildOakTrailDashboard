<?php
// Replaces the compare-table widget's html with the corrected version
// (flex wrapped in an inner span instead of set directly on <td>).

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$new_html = file_get_contents('/tmp/compare-table.html');
if ($new_html === false) {
    fwrite(STDERR, "Could not read compare-table.html\n");
    exit(1);
}

$widget_id = 'cmp0main';
$found = false;
function walk_and_set(&$node, $widget_id, $new_html, &$found) {
    if (!is_array($node)) return;
    if (isset($node['id']) && $node['id'] === $widget_id) {
        $node['settings']['html'] = $new_html;
        $found = true;
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk_and_set($child, $widget_id, $new_html, $found);
        }
    }
}

foreach ($data as &$section) {
    walk_and_set($section, $widget_id, $new_html, $found);
}

if (!$found) {
    fwrite(STDERR, "Widget cmp0main not found.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated compare-table widget html.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
