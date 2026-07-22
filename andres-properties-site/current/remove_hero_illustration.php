<?php
// Removes the hero background illustration widget (id hbi7a3f1) added
// earlier, per client feedback that the hero looks better without it.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$removed = false;
foreach ($data as &$section) {
    if (!isset($section['elements'])) continue;
    foreach ($section['elements'] as &$column) {
        if (!isset($column['elements'])) continue;
        foreach ($column['elements'] as $idx => $widget) {
            if (isset($widget['id']) && $widget['id'] === 'hbi7a3f1') {
                array_splice($column['elements'], $idx, 1);
                $removed = true;
            }
        }
    }
}

if (!$removed) {
    fwrite(STDERR, "Widget hbi7a3f1 not found -- nothing removed.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Removed hero illustration widget.\n";

$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
