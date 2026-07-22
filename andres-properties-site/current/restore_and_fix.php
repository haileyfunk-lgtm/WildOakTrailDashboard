<?php
// 1) Restores post 6's _elementor_data to the exact pre-edit state (from
//    /tmp/original_elementor_data_raw.json, the true DB string).
// 2) Re-applies the process-card widget edits correctly this time, with
//    wp_slash() before update_post_meta() -- WordPress's metadata API
//    internally wp_unslash()'s the value it's given, so raw JSON containing
//    backslash-escaped quotes MUST be slashed first or those backslashes
//    get silently stripped, corrupting the JSON (this is what broke the
//    page on the previous attempt).

$post_id = 6;
$original = file_get_contents('/tmp/original_elementor_data_raw.json');
if ($original === false) {
    fwrite(STDERR, "Could not read original data file\n");
    exit(1);
}

$data = json_decode($original, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode of original failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$replacements = [
    'b79569b' => [
        'old' => '<div class="process-card process-card-1">
  <span class="process-ghost-num" aria-hidden="true">1</span>
  <span class="process-rail-marker" aria-hidden="true"><span class="process-rail-marker-dot"></span></span>
  <h3>Tell us about the property</h3>
  <p>Share a few details about your home and situation.</p>
</div>',
        'new' => '<div class="process-card process-card-1">
  <span class="process-step-badge" aria-hidden="true"><span class="process-step-num">1</span></span>
  <h3>Tell us about the property</h3>
  <p>Share a few details about your home and situation.</p>
</div>',
    ],
    'f478935' => [
        'old' => '<div class="process-card process-card-2">
  <span class="process-ghost-num" aria-hidden="true">2</span>
  <span class="process-rail-marker" aria-hidden="true"><span class="process-rail-marker-dot"></span></span>
  <h3>Get a no-pressure cash offer</h3>
  <p>We review it and give you a straightforward offer.</p>
</div>',
        'new' => '<div class="process-card process-card-2">
  <span class="process-step-badge" aria-hidden="true"><span class="process-step-num">2</span></span>
  <h3>Get a no-pressure cash offer</h3>
  <p>We review it and give you a straightforward offer.</p>
</div>',
    ],
    'e4e5fed' => [
        'old' => '<div class="process-card process-card-3">
  <span class="process-ghost-num" aria-hidden="true">3</span>
  <span class="process-rail-marker" aria-hidden="true"><span class="process-rail-marker-dot"></span></span>
  <h3>Close when it works for you</h3>
  <p>Pick a timeline that fits your life.</p>
</div>',
        'new' => '<div class="process-card process-card-3">
  <span class="process-step-badge" aria-hidden="true"><span class="process-step-num">3</span></span>
  <h3>Close when it works for you</h3>
  <p>Pick a timeline that fits your life.</p>
</div>',
    ],
];

$found = [];
function walk_and_replace(&$node, $replacements, &$found) {
    if (!is_array($node)) return;
    if (isset($node['id']) && isset($replacements[$node['id']])) {
        $r = $replacements[$node['id']];
        if (isset($node['settings']['html']) && $node['settings']['html'] === $r['old']) {
            $node['settings']['html'] = $r['new'];
            $found[] = $node['id'];
        } else {
            fwrite(STDERR, "Widget {$node['id']} found but html did not match expected old value.\n");
        }
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk_and_replace($child, $replacements, $found);
        }
    }
}

foreach ($data as &$section) {
    walk_and_replace($section, $replacements, $found);
}

if (count($found) !== 3) {
    fwrite(STDERR, "Expected to update 3 widgets, updated: " . count($found) . " (" . implode(',', $found) . ")\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Restored + updated widgets: " . implode(',', $found) . "\n";
echo "New data length: " . strlen($new_json) . "\n";

// Verify round-trip immediately
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
echo "Contains process-step-badge: " . substr_count($check, 'process-step-badge') . "\n";
