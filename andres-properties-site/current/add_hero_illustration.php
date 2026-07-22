<?php
// Inserts a new decorative widget as the FIRST element of the hero's left
// column (id 4088e15), containing an ambient background SVG: a house icon
// connected by a rising dashed line to a cash/bundle icon, with a soft
// pulse at the end. Positioned absolute + very low opacity so it sits
// behind the existing text as ambient texture, not a competing element.
// Client asked for something in this spirit after seeing rankandfound.com's
// hero chart (rising line -> pulsing dot -> "#1" flag); this reskins that
// same "journey to a payoff" concept as house -> cash for a cash-offer
// home-buying business, instead of a growth chart (which doesn't fit).

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$illustration_html = '<div class="hero-bg-illustration" aria-hidden="true">
  <svg viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path class="hbi-path" d="M120 255 C 220 255, 300 180, 400 175 S 500 150, 545 148" stroke="url(#hbiLine)" stroke-width="3" stroke-linecap="round" stroke-dasharray="2 14"/>
    <defs>
      <linearGradient id="hbiLine" x1="120" y1="255" x2="545" y2="148" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#D1853F" stop-opacity="0.35"/>
        <stop offset="1" stop-color="#D38F4E" stop-opacity="0.85"/>
      </linearGradient>
    </defs>
    <g stroke="#F7F5F2" stroke-opacity="0.22" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none" transform="translate(40,210) scale(3.2)">
      <path d="M5 12l-2 0l9 -9l9 9l-2 0"/>
      <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"/>
      <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"/>
    </g>
    <circle class="hbi-pulse" cx="556" cy="136" r="28" fill="#D38F4E" opacity="0.14"/>
    <g stroke="#F7F5F2" stroke-opacity="0.4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none" transform="translate(520,100) scale(3)">
      <path d="M7 15h-3a1 1 0 0 1 -1 -1v-8a1 1 0 0 1 1 -1h12a1 1 0 0 1 1 1v3"/>
      <path d="M7 10a1 1 0 0 1 1 -1h12a1 1 0 0 1 1 1v8a1 1 0 0 1 -1 1h-12a1 1 0 0 1 -1 -1l0 -8"/>
      <path d="M12 14a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"/>
    </g>
  </svg>
</div>';

$new_widget = [
    'id' => 'hbi7a3f1',
    'elType' => 'widget',
    'widgetType' => 'html',
    'settings' => [
        'html' => $illustration_html,
    ],
    'elements' => [],
];

$inserted = false;
foreach ($data as &$section) {
    if (!isset($section['elements'])) continue;
    foreach ($section['elements'] as &$column) {
        if (isset($column['id']) && $column['id'] === '4088e15') {
            array_unshift($column['elements'], $new_widget);
            $inserted = true;
        }
    }
}

if (!$inserted) {
    fwrite(STDERR, "Column 4088e15 not found -- nothing inserted.\n");
    exit(1);
}

$new_json = wp_json_encode($data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Inserted hero illustration widget.\n";

$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
