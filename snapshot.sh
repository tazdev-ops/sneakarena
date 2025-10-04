#!/bin/bash

# Script to create a snapshot of all important code files in the project
# Output is saved to project_snapshot.txt

OUTPUT_FILE="project_snapshot.txt"
TEMP_DIR=$(mktemp -d)

echo "Creating project snapshot..."

# Add header to the output file
{
    echo "# LMArena Bridge Project Snapshot"
    echo "This file contains all important code and configuration files for the LMArena Bridge project."
    echo "Generated on: $(date)"
    echo "Directory: $(pwd)"
    echo ""
    echo "################################################################################"
    echo "# PROJECT STRUCTURE"
    echo "################################################################################"
    echo ""
    tree -a || find . -maxdepth 3 -type d | sed 's/^\.\//|-- /' | sed 's/\//|-- /g'
    echo ""
    echo "################################################################################"
    echo "# PROJECT FILES CONTENT"
    echo "################################################################################"
    echo ""
} > "$OUTPUT_FILE"

# Define the files and directories to include
FILES_TO_SNAPSHOT=(
    # Root files
    "__init__.py"
    ".editorconfig"
    "Dockerfile"
    "Makefile"
    "pre-commit-config.yaml"
    "pyproject.toml"
    "ruff.toml"
    
    # Main package
    "lmarena_bridge/__init__.py"
    "lmarena_bridge/logging_config.py"
    "lmarena_bridge/main.py"
    "lmarena_bridge/settings.py"
    
    # API module
    "lmarena_bridge/api"
    
    # Services module
    "lmarena_bridge/services"
    
    # Utils module
    "lmarena_bridge/utils"
    
    # GUI
    "lmarena_bridge_gui/__init__.py"
    "lmarena_bridge_gui/gtk_app.py"
    "lmarena_bridge_gui/ui"
    "lmarena_bridge_gui/utils"
    
    # Configuration
    "config"
    
    # Tests
    "tests"
    
    # Documentation
    "docs"
    
    # Packaging
    "packaging"
    
    # Public assets
    "public"
)

# Process each file/directory
for item in "${FILES_TO_SNAPSHOT[@]}"; do
    if [[ -f "$item" ]]; then
        echo "Processing file: $item" >&2
        {
            echo ""
            echo "################################################################################"
            echo "# FILE: $item"
            echo "################################################################################"
            cat "$item"
            echo ""
        } >> "$OUTPUT_FILE"
    elif [[ -d "$item" ]]; then
        echo "Processing directory: $item" >&2
        find "$item" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.md" -o -name "*.txt" -o -name "*.cfg" -o -name "*.ini" -o -name "Dockerfile*" -o -name "Makefile*" \) -exec sh -c '
            echo ""
            echo "################################################################################"
            echo "# FILE: {}"
            echo "################################################################################"
            cat "$1"
            echo ""
        ' _ {} \; >> "$OUTPUT_FILE"
    fi
done

echo "Snapshot completed. Output saved to $OUTPUT_FILE"
echo "File size: $(wc -c < "$OUTPUT_FILE") bytes"