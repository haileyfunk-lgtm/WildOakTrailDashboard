<?php
// Swaps the 6 hand-rolled situation-card icon SVGs for real Tabler Icons
// (MIT-licensed, https://tabler.io/icons) paths, matching the concept more
// precisely (e.g. a gavel for Foreclosure instead of an ambiguous
// house+shield shape) and rendering more cleanly. Keeps the same
// stroke-width (1.6) already established for icons on this page. Only the
// <svg>...</svg> markup changes -- card wrapper classes, h3, p untouched.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$replacements = [
    '57137ea' => [
        'old' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V9l8-5 8 5v12"/><path d="M4 21h16"/><path d="M12 21v-5"/><path d="M9 12h6"/></svg></div>
  <h3>Inherited Property</h3>
  <p>Handling a home you\'ve inherited without the hassle of prepping it for sale.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l-2 0l9 -9l9 9l-2 0"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"/><path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"/></svg></div>
  <h3>Inherited Property</h3>
  <p>Handling a home you\'ve inherited without the hassle of prepping it for sale.</p>
</div>',
    ],
    'e8472d3' => [
        'old' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10 12 4l8 6v10H4z"/><path d="M8 20v-6h8v6"/><path d="M15 5l4 4"/><path d="M19 5l-4 4"/></svg></div>
  <h3>Foreclosure</h3>
  <p>A private, faster path forward when time isn\'t on your side.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 10l7.383 7.418c.823 .82 .823 2.148 0 2.967a2.11 2.11 0 0 1 -2.976 0l-7.407 -7.385"/><path d="M6 9l4 4"/><path d="M13 10l-4 -4"/><path d="M3 21h7"/><path d="M6.793 15.793l-3.586 -3.586a1 1 0 0 1 0 -1.414l2.293 -2.293l.5 .5l3 -3l-.5 -.5l2.293 -2.293a1 1 0 0 1 1.414 0l3.586 3.586a1 1 0 0 1 0 1.414l-2.293 2.293l-.5 -.5l-3 3l.5 .5l-2.293 2.293a1 1 0 0 1 -1.414 0"/></svg></div>
  <h3>Foreclosure</h3>
  <p>A private, faster path forward when time isn\'t on your side.</p>
</div>',
    ],
    'd686aa0' => [
        'old' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21S4 14.5 4 8.8A4 4 0 0 1 12 7a4 4 0 0 1 8 1.8c0 1.4-.5 2.7-1.3 3.9"/><path d="M14 14l6 6"/><path d="M20 14l-6 6"/></svg></div>
  <h3>Divorce or Separation</h3>
  <p>A simple sale so you can both move forward.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"/><path d="M12 6l-2 4l4 3l-2 4v3"/></svg></div>
  <h3>Divorce or Separation</h3>
  <p>A simple sale so you can both move forward.</p>
</div>',
    ],
    '42e37eb' => [
        'old' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="7" r="3.2"/><path d="M5 21v-1a7 7 0 0 1 14 0v1"/><path d="M2 4l20 16"/></svg></div>
  <h3>Problem Tenants</h3>
  <p>Sell as-is, tenants and all, without the landlord headaches.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8.18 8.189a4.01 4.01 0 0 0 2.616 2.627m3.507 -.545a4 4 0 1 0 -5.59 -5.552"/><path d="M6 21v-2a4 4 0 0 1 4 -4h4c.412 0 .81 .062 1.183 .178m2.633 2.618c.12 .38 .184 .785 .184 1.204v2"/><path d="M3 3l18 18"/></svg></div>
  <h3>Problem Tenants</h3>
  <p>Sell as-is, tenants and all, without the landlord headaches.</p>
</div>',
    ],
    'a1982d4' => [
        'old' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10 12 4l8 6v10H4z"/><rect x="9" y="12" width="6" height="8"/><path d="M12 12v8"/></svg></div>
  <h3>Vacant House</h3>
  <p>Stop paying to maintain a home that\'s just sitting empty.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-copper">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h-2l4.497 -4.497m2 -2l2.504 -2.504l9 9h-2"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2m0 -4v-3"/><path d="M9 21v-6a2 2 0 0 1 2 -2h2m2 2v6"/><path d="M3 3l18 18"/></svg></div>
  <h3>Vacant House</h3>
  <p>Stop paying to maintain a home that\'s just sitting empty.</p>
</div>',
    ],
    'e8fc755' => [
        'old' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a3 3 0 0 0-4.2 4.2L4 17l3 3 6.5-6.5a3 3 0 0 0 4.2-4.2l-2.1 2.1-2-2z"/></svg></div>
  <h3>Major Repairs Needed</h3>
  <p>Fire, water, or structural damage &mdash; sell without fixing a thing.</p>
</div>',
        'new' => '<div class="situation-card situation-accent-navy">
  <div class="bar"></div>
  <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5"/></svg></div>
  <h3>Major Repairs Needed</h3>
  <p>Fire, water, or structural damage &mdash; sell without fixing a thing.</p>
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

if (count($found) !== 6) {
    fwrite(STDERR, "Expected to update 6 widgets, updated: " . count($found) . " (" . implode(',', $found) . ")\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Updated widgets: " . implode(',', $found) . "\n";

$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
