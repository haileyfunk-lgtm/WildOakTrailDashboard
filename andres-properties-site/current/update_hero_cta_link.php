<?php
// Changes the hero "Tell Us About Your Property" button from linking to
// the separate /contact/ page to anchoring down to the #contact section
// on the homepage, matching how the header's "Get a Cash Offer" link
// (and FAQ/Reviews) already work as on-page anchors.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$widget_id = '2e2d70c';
$old_html = '<div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:32px;">
  <a href="https://powderblue-trout-602145.hostingersite.com/contact/" style="text-decoration:none; background:#D1853F; color:#fff; padding:17px 32px; border-radius:999px; font-size:16px; font-weight:600; box-shadow:0 6px 16px rgba(209,133,63,0.32); font-family:\'Work Sans\',sans-serif; display:inline-block;">Tell Us About Your Property</a>
  <a href="tel:12043713559" style="text-decoration:none; border:1px solid #33395a; color:#F7F5F2; padding:17px 32px; border-radius:999px; font-size:16px; font-weight:600; box-shadow:0 4px 12px rgba(0,0,0,0.2); font-family:\'Work Sans\',sans-serif; display:inline-block;">Call Jason Directly</a>
</div>';
$new_html = '<div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:32px;">
  <a href="https://powderblue-trout-602145.hostingersite.com/#contact" style="text-decoration:none; background:#D1853F; color:#fff; padding:17px 32px; border-radius:999px; font-size:16px; font-weight:600; box-shadow:0 6px 16px rgba(209,133,63,0.32); font-family:\'Work Sans\',sans-serif; display:inline-block;">Tell Us About Your Property</a>
  <a href="tel:12043713559" style="text-decoration:none; border:1px solid #33395a; color:#F7F5F2; padding:17px 32px; border-radius:999px; font-size:16px; font-weight:600; box-shadow:0 4px 12px rgba(0,0,0,0.2); font-family:\'Work Sans\',sans-serif; display:inline-block;">Call Jason Directly</a>
</div>';

$found = false;
function walk_and_replace(&$node, $widget_id, $old_html, $new_html, &$found) {
    if (!is_array($node)) return;
    if (isset($node['id']) && $node['id'] === $widget_id) {
        if (isset($node['settings']['html']) && $node['settings']['html'] === $old_html) {
            $node['settings']['html'] = $new_html;
            $found = true;
        } else {
            fwrite(STDERR, "Widget $widget_id found but html did not match expected old value.\n");
        }
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk_and_replace($child, $widget_id, $old_html, $new_html, $found);
        }
    }
}

foreach ($data as &$section) {
    walk_and_replace($section, $widget_id, $old_html, $new_html, $found);
}

if (!$found) {
    fwrite(STDERR, "Widget not updated.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated hero CTA link.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
