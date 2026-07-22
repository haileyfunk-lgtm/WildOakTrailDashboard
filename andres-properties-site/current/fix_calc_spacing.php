<?php
// Reduces the calculator section's bottom padding (100px -> 40px). The
// Situations section right after it already has its own 90px top padding,
// so the combined 190px gap was reading as an oversized dead zone between
// the CTA button and "Whatever brought you here, we understand."

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$found = false;
foreach ($data as &$section) {
    if (isset($section['settings']['_element_id']) && $section['settings']['_element_id'] === 'calculator') {
        $section['settings']['padding']['bottom'] = '40';
        $found = true;
    }
}

if (!$found) {
    fwrite(STDERR, "calculator section not found.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated calculator section bottom padding to 40px.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
