<?php
// Inserts a "Traditional vs. Us" comparison table section directly above
// the Reviews section (after case-study, before the reviews heading).

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$table_html = file_get_contents('/tmp/compare-table.html');
if ($table_html === false) {
    fwrite(STDERR, "Could not read compare-table.html\n");
    exit(1);
}

$new_section = [
    'id' => 'cmp0001',
    'elType' => 'section',
    'settings' => [
        'background_color' => '#F7F5F2',
        'background_background' => 'classic',
        'layout' => 'full_width',
        '_element_id' => 'compare-table',
        'padding' => ['unit' => 'px', 'top' => '100', 'right' => '40', 'bottom' => '100', 'left' => '40'],
    ],
    'elements' => [
        [
            'id' => 'cmp0col',
            'elType' => 'column',
            'settings' => ['_column_size' => 100],
            'elements' => [
                [
                    'id' => 'cmp0kick',
                    'elType' => 'widget',
                    'widgetType' => 'html',
                    'settings' => [
                        'html' => '<div class="kicker">The Comparison</div>',
                        '_css_classes' => 'reveal-up',
                    ],
                    'elements' => [],
                ],
                [
                    'id' => 'cmp0head',
                    'elType' => 'widget',
                    'widgetType' => 'heading',
                    'settings' => [
                        'title' => 'Traditional Sale vs. Selling to Us',
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
                    'id' => 'cmp0spc1',
                    'elType' => 'widget',
                    'widgetType' => 'spacer',
                    'settings' => ['space' => ['unit' => 'px', 'size' => 30]],
                    'elements' => [],
                ],
                [
                    'id' => 'cmp0main',
                    'elType' => 'widget',
                    'widgetType' => 'html',
                    'settings' => [
                        'html' => $table_html,
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
    if (isset($section['settings']['_element_id']) && $section['settings']['_element_id'] === 'case-study') {
        $new_data[] = $new_section;
        $inserted = true;
    }
}

if (!$inserted) {
    fwrite(STDERR, "case-study section not found -- nothing inserted.\n");
    exit(1);
}

$new_json = wp_json_encode($new_data);
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

echo "Inserted comparison table section.\n";
$check = get_post_meta($post_id, '_elementor_data', true);
$check_decoded = json_decode($check, true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO (" . json_last_error_msg() . ")") . "\n";
echo "Post-write section count: " . (is_array($check_decoded) ? count($check_decoded) : 'N/A') . "\n";
