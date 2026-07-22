<?php
// Updates only the 3 process-card HTML widgets on the Home page (post 6),
// replacing the old ghost-numeral + rail-marker-dot markup with the new
// step-badge markup. Leaves every other widget/section untouched.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
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
update_post_meta($post_id, '_elementor_data', $new_json);
echo "Updated widgets: " . implode(',', $found) . "\n";
echo "New data length: " . strlen($new_json) . "\n";
