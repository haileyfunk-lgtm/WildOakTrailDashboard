<?php
// Points the hero photo widget at jason-headshot-v2.jpg instead of
// jason-headshot.jpg. Not a quality re-fix (that file's already updated) --
// this is a cache-busting rename so browsers/CDN that cached the old low-
// res photo at the old URL (cache-control: max-age=31536000, one year)
// are forced to fetch fresh instead of reusing a stale cached copy.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$widget_id = 'affa2de'; // hero photo widget, found earlier in this project
$old_needle = 'jason-headshot.jpg';
$new_value = 'jason-headshot-v2.jpg';

$found = false;
function walk_and_replace(&$node, $widget_id, $old_needle, $new_value, &$found) {
    if (!is_array($node)) return;
    if (isset($node['id']) && $node['id'] === $widget_id) {
        if (isset($node['settings']['html']) && strpos($node['settings']['html'], $old_needle) !== false) {
            $node['settings']['html'] = str_replace($old_needle, $new_value, $node['settings']['html']);
            $found = true;
        } else {
            fwrite(STDERR, "Widget $widget_id found but expected string not present.\n");
        }
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk_and_replace($child, $widget_id, $old_needle, $new_value, $found);
        }
    }
}

foreach ($data as &$section) {
    walk_and_replace($section, $widget_id, $old_needle, $new_value, $found);
}

if (!$found) {
    fwrite(STDERR, "Widget not updated.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated hero photo src to jason-headshot-v2.jpg\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
