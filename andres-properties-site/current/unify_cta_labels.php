<?php
// Standardises every "start the conversation" CTA on the home page to a
// single label.
//
// The page had three different labels for one intent:
//   nav menu item ......... "Get a Cash Offer"   (WP menu, not Elementor)
//   footer link ........... "Get a Cash Offer"   (WP widget, not Elementor)
//   hero primary button ... "Tell Us About Your Property"   <- widget 2e2d70c
//   contact form button ... "Get My Cash Offer"             <- widget 3469471
//
// "Get a Cash Offer" wins because it already covers two of the four
// placements and it names the outcome rather than the mechanism.
// "Call Jason Directly" is deliberately NOT touched: placing a phone call is
// a genuinely different action, so it should keep a distinct label.
//
// Both targets are raw HTML widgets, so the label lives inside the widget's
// `html` setting rather than a `text` field. Replacements are anchored to the
// closing tag so a bare occurrence of the phrase elsewhere in the markup
// (a title attribute, a comment) can't be hit by accident.

$post_id = 6;
$raw = get_post_meta($post_id, '_elementor_data', true);
$data = json_decode($raw, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    fwrite(STDERR, "JSON decode failed: " . json_last_error_msg() . "\n");
    exit(1);
}

$edits = [
    '2e2d70c' => ['>Tell Us About Your Property</a>', '>Get a Cash Offer</a>'],
    '3469471' => ['>Get My Cash Offer</button>',      '>Get a Cash Offer</button>'],
];

$applied = [];

function walk(&$node, $edits, &$applied) {
    if (!is_array($node)) return;
    if (isset($node['id'], $node['settings']['html']) && isset($edits[$node['id']])) {
        list($from, $to) = $edits[$node['id']];
        $count = 0;
        $node['settings']['html'] = str_replace($from, $to, $node['settings']['html'], $count);
        $applied[$node['id']] = $count;
    }
    if (isset($node['elements']) && is_array($node['elements'])) {
        foreach ($node['elements'] as &$child) {
            walk($child, $edits, $applied);
        }
    }
}

foreach ($data as &$section) {
    walk($section, $edits, $applied);
}

// Fail loudly rather than silently writing an unchanged blob: if a widget id
// moved or the markup drifted, str_replace returns 0 and we want to know
// before the DB is touched.
foreach ($edits as $id => $_) {
    if (!isset($applied[$id])) {
        fwrite(STDERR, "Widget $id not found. Aborting, nothing written.\n");
        exit(1);
    }
    if ($applied[$id] < 1) {
        fwrite(STDERR, "Widget $id found but its label did not match. Aborting, nothing written.\n");
        exit(1);
    }
}

$new_json = wp_json_encode($data);
if ($new_json === false) {
    fwrite(STDERR, "Re-encode failed. Aborting.\n");
    exit(1);
}
update_post_meta($post_id, '_elementor_data', wp_slash($new_json));

foreach ($applied as $id => $n) {
    echo "  $id: $n replacement(s)\n";
}
$check = json_decode(get_post_meta($post_id, '_elementor_data', true), true);
echo "Post-write JSON valid: " . (json_last_error() === JSON_ERROR_NONE ? "YES" : "NO") . "\n";
echo "Post-write section count: " . (is_array($check) ? count($check) : 'N/A') . "\n";
