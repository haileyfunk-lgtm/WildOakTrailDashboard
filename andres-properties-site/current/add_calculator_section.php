<?php
// Inserts a new "Cost Comparison" calculator section between Meet Jason
// and Situations We Help With, replicating the mechanism of the
// hannybuyshouses.ca calculator (home-value slider driving a traditional-
// sale-costs vs. cash-offer-net comparison) with Andres Properties brand
// colors, fonts, and original wording.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$calc_html = file_get_contents('/tmp/calculator-widget.html');
if ($calc_html === false) {
    fwrite(STDERR, "Could not read calculator-widget.html\n");
    exit(1);
}

$new_section = [
    'id' => 'cLc0001',
    'elType' => 'section',
    'settings' => [
        'background_color' => '#F7F5F2',
        'background_background' => 'classic',
        'layout' => 'full_width',
        '_element_id' => 'calculator',
        'padding' => ['unit' => 'px', 'top' => '100', 'right' => '40', 'bottom' => '100', 'left' => '40'],
    ],
    'elements' => [
        [
            'id' => 'cLc0col',
            'elType' => 'column',
            'settings' => ['_column_size' => 100],
            'elements' => [
                [
                    'id' => 'cLc0kick',
                    'elType' => 'widget',
                    'widgetType' => 'html',
                    'settings' => [
                        'html' => '<div class="kicker">Cost Comparison</div>',
                        '_css_classes' => 'reveal-up',
                    ],
                    'elements' => [],
                ],
                [
                    'id' => 'cLc0head',
                    'elType' => 'widget',
                    'widgetType' => 'heading',
                    'settings' => [
                        'title' => "See What You'd Actually Walk Away With",
                        'header_size' => 'h2',
                        'align' => 'center',
                        'title_color' => '#071337',
                        'typography_font_size' => ['unit' => 'px', 'size' => 42],
                        'typography_typography' => 'custom',
                        '_css_classes' => 'reveal-up',
                    ],
                    'elements' => [],
                ],
                [
                    'id' => 'cLc0desc',
                    'elType' => 'widget',
                    'widgetType' => 'text-editor',
                    'settings' => [
                        'editor' => '<p>Compare a traditional listing to a private cash sale with Andres Properties, side by side, dollar for dollar.</p>',
                        'align' => 'center',
                        '_css_classes' => 'reveal-up',
                    ],
                    'elements' => [],
                ],
                [
                    'id' => 'cLc0spc1',
                    'elType' => 'widget',
                    'widgetType' => 'spacer',
                    'settings' => ['space' => ['unit' => 'px', 'size' => 30]],
                    'elements' => [],
                ],
                [
                    'id' => 'cLc0main',
                    'elType' => 'widget',
                    'widgetType' => 'html',
                    'settings' => [
                        'html' => $calc_html,
                        '_css_classes' => 'reveal-up',
                    ],
                    'elements' => [],
                ],
            ],
            'isInner' => false,
        ],
    ],
    'isInner' => false,
];

$inserted = false;
$new_data = [];
foreach ($data as $section) {
    $new_data[] = $section;
    if (isset($section['settings']['_element_id']) && $section['settings']['_element_id'] === 'meet-jason') {
        $new_data[] = $new_section;
        $inserted = true;
    }
}

if (!$inserted) {
    fwrite(STDERR, "meet-jason section not found -- nothing inserted.\n");
    exit(1);
}

$new_json = wp_json_encode($new_data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Inserted calculator section.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
