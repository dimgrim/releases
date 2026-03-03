<?php
header('Content-Type: application/json');

$sounds_dir = './sounds';
$response = [
    'note_folders' => [],
    'background_files' => [],
    'note_files' => []
];

// Get all subfolders in sounds directory (for note folders)
if (is_dir($sounds_dir)) {
    $items = scandir($sounds_dir);
    foreach ($items as $item) {
        if ($item != '.' && $item != '..' && is_dir($sounds_dir . '/' . $item)) {
            if ($item != 'background') { // Exclude background folder from note folders
                $response['note_folders'][] = $item;
                
                // Get note files from this folder
                $note_folder = $sounds_dir . '/' . $item;
                $files = scandir($note_folder);
                $note_files = [];
                foreach ($files as $file) {
                    if (pathinfo($file, PATHINFO_EXTENSION) == 'wav') {
                        $note_files[] = $file;
                    }
                }
                $response['note_files'][$item] = $note_files;
            }
        }
    }
}

// Get background files
$bg_dir = $sounds_dir . '/background';
if (is_dir($bg_dir)) {
    $files = scandir($bg_dir);
    foreach ($files as $file) {
        if (pathinfo($file, PATHINFO_EXTENSION) == 'wav') {
            $response['background_files'][] = $file;
        }
    }
}

echo json_encode($response);
?>
