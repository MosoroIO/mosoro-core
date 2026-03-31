#!/usr/bin/env bash
# Copyright 2026 Mosoro Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# ============================================================================
# Mosoro Setup Wizard
# ============================================================================
# Interactive setup for selecting robot adapters, configuring connections,
# and generating robots.yaml + .env files.
#
# Usage:
#   ./scripts/setup-wizard.sh          # Full setup
#   ./scripts/setup-wizard.sh --add    # Add another robot to existing config
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CATALOG_FILE="$PROJECT_DIR/catalog.json"
ROBOTS_YAML="$PROJECT_DIR/robots.yaml"
ENV_FILE="$PROJECT_DIR/.env"

# Colors (safe for non-color terminals)
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    BOLD=$(tput bold)
    CYAN=$(tput setaf 6)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    RED=$(tput setaf 1)
    DIM=$(tput dim)
    RESET=$(tput sgr0)
else
    BOLD="" CYAN="" GREEN="" YELLOW="" RED="" DIM="" RESET=""
fi

# ---------------------------------------------------------------------------
# JSON parsing helpers — prefer jq, fall back to Python
# ---------------------------------------------------------------------------
HAS_JQ=false
if command -v jq &>/dev/null; then
    HAS_JQ=true
fi

json_query() {
    # Usage: json_query <file> <jq_filter>
    local file="$1" filter="$2"
    if $HAS_JQ; then
        jq -r "$filter" "$file"
    else
        python3 -c "
import json, sys
with open('$file') as f:
    data = json.load(f)
# Evaluate the jq-like filter using a simple mapping
filt = '''$filter'''
# Handle simple cases used in this script
if filt == '.extensions[] | select(.category==\"robots\") | .id':
    for e in data['extensions']:
        if e['category'] == 'robots':
            print(e['id'])
elif filt.startswith('.extensions[] | select(.id=='):
    target_id = filt.split('\"')[1]
    for e in data['extensions']:
        if e['id'] == target_id:
            import json as j
            print(j.dumps(e))
            break
else:
    print('')
"
    fi
}

json_field() {
    # Extract a field from a JSON string
    # Usage: echo '{"a":1}' | json_field .a
    local filter="$1"
    if $HAS_JQ; then
        jq -r "$filter"
    else
        python3 -c "
import json, sys
data = json.load(sys.stdin)
keys = '''$filter'''.lstrip('.').split('.')
val = data
for k in keys:
    if k == '':
        continue
    val = val[k]
print(val if val is not None else '')
"
    fi
}

json_array_length() {
    # Get length of a JSON array from stdin
    if $HAS_JQ; then
        jq 'length'
    else
        python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
    fi
}

json_array_item() {
    # Get item at index from JSON array on stdin
    # Usage: echo '[...]' | json_array_item 0 .name
    local idx="$1" field="$2"
    if $HAS_JQ; then
        jq -r ".[$idx]$field"
    else
        python3 -c "
import json, sys
data = json.load(sys.stdin)
item = data[$idx]
keys = '''$field'''.lstrip('.').split('.')
val = item
for k in keys:
    if k == '':
        continue
    val = val[k]
print(val if val is not None else '')
"
    fi
}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
banner() {
    echo ""
    echo "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${RESET}"
    echo "${BOLD}${CYAN}║              🤖  Mosoro Setup Wizard  🤖               ║${RESET}"
    echo "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

info()    { echo "${GREEN}✓${RESET} $*"; }
warn()    { echo "${YELLOW}⚠${RESET} $*"; }
error()   { echo "${RED}✗${RESET} $*" >&2; }
step()    { echo ""; echo "${BOLD}${CYAN}▸ $*${RESET}"; }

generate_secret() {
    # Generate a cryptographically secure random string
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null \
        || openssl rand -base64 32 2>/dev/null \
        || head -c 32 /dev/urandom | base64 | tr -d '=/+' | head -c 32
}

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
check_prerequisites() {
    if [[ ! -f "$CATALOG_FILE" ]]; then
        error "catalog.json not found at $CATALOG_FILE"
        error "Are you running this from the mosoro-core directory?"
        exit 1
    fi

    if ! command -v python3 &>/dev/null && ! $HAS_JQ; then
        error "Either 'jq' or 'python3' is required. Please install one."
        exit 1
    fi

    if ! command -v pip &>/dev/null && ! command -v pip3 &>/dev/null; then
        warn "pip not found. Adapter installation will be skipped."
        warn "Install pip and re-run, or install adapters manually."
    fi
}

# ---------------------------------------------------------------------------
# Get the pip command
# ---------------------------------------------------------------------------
get_pip_cmd() {
    if command -v pip3 &>/dev/null; then
        echo "pip3"
    elif command -v pip &>/dev/null; then
        echo "pip"
    else
        echo ""
    fi
}

# ---------------------------------------------------------------------------
# Show available robot adapters from catalog
# ---------------------------------------------------------------------------
show_robot_catalog() {
    step "Available Robot Adapters"
    echo ""

    local ids
    ids=$(json_query "$CATALOG_FILE" '.extensions[] | select(.category=="robots") | .id')

    local idx=1
    while IFS= read -r ext_id; do
        local ext_json
        ext_json=$(json_query "$CATALOG_FILE" ".extensions[] | select(.id==\"$ext_id\")")

        local name conn_type desc
        name=$(echo "$ext_json" | json_field .name)
        conn_type=$(echo "$ext_json" | json_field .connection_type)
        desc=$(echo "$ext_json" | json_field .description)

        printf "  ${BOLD}%d)${RESET} %-35s ${DIM}[%s]${RESET}\n" "$idx" "$name" "$conn_type"
        printf "     ${DIM}%s${RESET}\n" "$desc"
        idx=$((idx + 1))
    done <<< "$ids"

    echo ""
    printf "  ${BOLD}%d)${RESET} %-35s ${DIM}[Custom]${RESET}\n" "$idx" "Other / Not listed"
    printf "     ${DIM}Build your own adapter or hire Mosoro${RESET}\n"
}

# ---------------------------------------------------------------------------
# Get robot IDs list from catalog
# ---------------------------------------------------------------------------
get_robot_ids() {
    json_query "$CATALOG_FILE" '.extensions[] | select(.category=="robots") | .id'
}

# ---------------------------------------------------------------------------
# Prompt for adapter selection
# ---------------------------------------------------------------------------
select_adapters() {
    local ids_str
    ids_str=$(get_robot_ids)

    # Convert to array
    local -a ids=()
    while IFS= read -r line; do
        ids+=("$line")
    done <<< "$ids_str"

    local max_idx=${#ids[@]}
    local other_idx=$((max_idx + 1))

    echo "  Enter adapter numbers (comma-separated), e.g.: ${BOLD}1,3${RESET}"
    echo ""
    read -rp "  ${BOLD}Your selection: ${RESET}" selection

    # Parse selection
    SELECTED_ADAPTERS=()
    IFS=',' read -ra choices <<< "$selection"
    for choice in "${choices[@]}"; do
        choice=$(echo "$choice" | tr -d ' ')
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
            if [[ "$choice" -ge 1 && "$choice" -le "$max_idx" ]]; then
                SELECTED_ADAPTERS+=("${ids[$((choice - 1))]}")
            elif [[ "$choice" -eq "$other_idx" ]]; then
                show_custom_adapter_info
            else
                warn "Invalid selection: $choice (skipped)"
            fi
        fi
    done

    if [[ ${#SELECTED_ADAPTERS[@]} -eq 0 ]]; then
        error "No valid adapters selected. Exiting."
        exit 1
    fi

    echo ""
    info "Selected adapters: ${BOLD}${SELECTED_ADAPTERS[*]}${RESET}"
}

# ---------------------------------------------------------------------------
# Show info for custom/unlisted adapters
# ---------------------------------------------------------------------------
show_custom_adapter_info() {
    echo ""
    echo "  ${BOLD}Your robot vendor isn't listed yet?${RESET}"
    echo ""
    echo "  ${CYAN}Option A:${RESET} Build your own adapter"
    echo "    See: mosoro-adapters-community/adapters/_template/"
    echo "    Docs: https://docs.mosoro.io/adapters/build-your-own"
    echo ""
    echo "  ${CYAN}Option B:${RESET} Hire Mosoro to build it"
    echo "    Contact: adapters@mosoro.io"
    echo "    We typically deliver custom adapters in 2-4 weeks."
    echo ""
}

# ---------------------------------------------------------------------------
# Install selected adapters via pip
# ---------------------------------------------------------------------------
install_adapters() {
    local pip_cmd
    pip_cmd=$(get_pip_cmd)

    if [[ -z "$pip_cmd" ]]; then
        warn "pip not available — skipping adapter installation."
        warn "Install adapters manually: pip install mosoro-adapter-<vendor>"
        return 0
    fi

    step "Installing Adapters"

    for adapter_id in "${SELECTED_ADAPTERS[@]}"; do
        local ext_json pkg_name
        ext_json=$(json_query "$CATALOG_FILE" ".extensions[] | select(.id==\"$adapter_id\")")
        pkg_name=$(echo "$ext_json" | json_field .package)

        echo "  Installing ${BOLD}$pkg_name${RESET}..."
        if $pip_cmd install "$pkg_name" 2>/dev/null; then
            info "Installed $pkg_name"
        else
            warn "Failed to install $pkg_name"
            warn "You can install it later: $pip_cmd install $pkg_name"
            warn "Continuing with configuration..."
        fi
    done
}

# ---------------------------------------------------------------------------
# Configure robots — prompt for connection details
# ---------------------------------------------------------------------------
configure_robots() {
    step "Configure Robot Connections"

    ROBOT_CONFIGS=()

    for adapter_id in "${SELECTED_ADAPTERS[@]}"; do
        configure_vendor_robots "$adapter_id"
    done
}

configure_vendor_robots() {
    local vendor_id="$1"
    local ext_json
    ext_json=$(json_query "$CATALOG_FILE" ".extensions[] | select(.id==\"$vendor_id\")")

    local vendor_name
    vendor_name=$(echo "$ext_json" | json_field .name)

    echo ""
    echo "  ${BOLD}$vendor_name${RESET}"

    local add_more=true
    local robot_count=0

    while $add_more; do
        robot_count=$((robot_count + 1))
        local robot_id="${vendor_id}-$(printf '%03d' $robot_count)"

        echo ""
        echo "  Configuring robot: ${BOLD}$robot_id${RESET}"

        local config_entry="  - id: $robot_id"
        config_entry="$config_entry
    vendor: $vendor_id"

        # Get config fields from catalog
        local fields_json
        if $HAS_JQ; then
            fields_json=$(echo "$ext_json" | jq -c '.config_fields // []')
        else
            fields_json=$(echo "$ext_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data.get('config_fields', [])))
")
        fi

        local num_fields
        num_fields=$(echo "$fields_json" | json_array_length)

        local i=0
        while [[ $i -lt $num_fields ]]; do
            local field_name field_label field_type field_default default_port path_suffix
            field_name=$(echo "$fields_json" | json_array_item "$i" .name)
            field_label=$(echo "$fields_json" | json_array_item "$i" .label)
            field_type=$(echo "$fields_json" | json_array_item "$i" .type)

            # Get defaults (may be null/empty)
            if $HAS_JQ; then
                field_default=$(echo "$fields_json" | jq -r ".[$i].default // empty")
                default_port=$(echo "$fields_json" | jq -r ".[$i].default_port // empty")
                path_suffix=$(echo "$fields_json" | jq -r ".[$i].path_suffix // empty")
            else
                field_default=$(echo "$fields_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
val = data[$i].get('default', '')
print(val if val else '')
")
                default_port=$(echo "$fields_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
val = data[$i].get('default_port', '')
print(val if val else '')
")
                path_suffix=$(echo "$fields_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
val = data[$i].get('path_suffix', '')
print(val if val else '')
")
            fi

            local prompt_text="    $field_label"
            local value=""

            if [[ "$field_type" == "host" ]]; then
                # For host fields, prompt for IP/hostname and build URL
                local port_hint=""
                [[ -n "$default_port" ]] && port_hint=" (port: $default_port)"
                read -rp "    ${field_label}${port_hint}: " host_input

                if [[ -z "$host_input" ]]; then
                    warn "    Skipped — using placeholder"
                    value="http://CHANGE_ME:${default_port:-8080}${path_suffix}"
                else
                    # If user provided a full URL, use it as-is
                    if [[ "$host_input" =~ ^https?:// ]]; then
                        value="$host_input"
                    else
                        value="http://${host_input}:${default_port:-8080}${path_suffix}"
                    fi
                fi
                config_entry="$config_entry
    $field_name: \"$value\""

            elif [[ "$field_type" == "secret" ]]; then
                read -rsp "    ${field_label} (hidden): " secret_input
                echo ""
                if [[ -z "$secret_input" ]]; then
                    value="CHANGE_ME"
                else
                    value="$secret_input"
                fi
                config_entry="$config_entry
    $field_name: \"$value\""

            elif [[ "$field_type" == "text" ]]; then
                local default_hint=""
                [[ -n "$field_default" ]] && default_hint=" [default: $field_default]"
                read -rp "    ${field_label}${default_hint}: " text_input
                value="${text_input:-$field_default}"
                config_entry="$config_entry
    $field_name: \"$value\""
            fi

            i=$((i + 1))
        done

        ROBOT_CONFIGS+=("$config_entry")
        info "  Configured $robot_id"

        # Ask if user wants to add another robot of the same vendor
        echo ""
        read -rp "  Add another ${vendor_name}? [y/N]: " add_another
        if [[ ! "$add_another" =~ ^[Yy] ]]; then
            add_more=false
        fi
    done
}

# ---------------------------------------------------------------------------
# Generate robots.yaml
# ---------------------------------------------------------------------------
generate_robots_yaml() {
    step "Generating robots.yaml"

    local yaml_content="# Mosoro Robot Configuration
# Auto-generated by: make setup
# Add robots manually or re-run: make add-robot
#
# Each robot needs:
#   - id: unique identifier
#   - vendor: adapter name (must be installed)
#   - connection details specific to the vendor

robots:"

    for config in "${ROBOT_CONFIGS[@]}"; do
        yaml_content="$yaml_content
$config
"
    done

    if [[ -f "$ROBOTS_YAML" ]]; then
        warn "robots.yaml already exists."
        read -rp "  Overwrite? [y/N]: " overwrite
        if [[ ! "$overwrite" =~ ^[Yy] ]]; then
            local backup="${ROBOTS_YAML}.bak.$(date +%s)"
            cp "$ROBOTS_YAML" "$backup"
            info "Backed up existing config to $backup"
        fi
    fi

    echo "$yaml_content" > "$ROBOTS_YAML"
    info "Generated ${BOLD}robots.yaml${RESET} with ${#ROBOT_CONFIGS[@]} robot(s)"
}

# ---------------------------------------------------------------------------
# Append robots to existing robots.yaml (--add mode)
# ---------------------------------------------------------------------------
append_robots_yaml() {
    step "Adding robots to existing robots.yaml"

    if [[ ! -f "$ROBOTS_YAML" ]]; then
        warn "No existing robots.yaml found. Running full setup instead."
        generate_robots_yaml
        return
    fi

    for config in "${ROBOT_CONFIGS[@]}"; do
        echo "" >> "$ROBOTS_YAML"
        echo "$config" >> "$ROBOTS_YAML"
    done

    info "Added ${#ROBOT_CONFIGS[@]} robot(s) to ${BOLD}robots.yaml${RESET}"
}

# ---------------------------------------------------------------------------
# Generate .env with smart defaults
# ---------------------------------------------------------------------------
generate_env() {
    step "Generating .env"

    if [[ -f "$ENV_FILE" ]]; then
        info ".env already exists — skipping generation."
        info "Edit manually or delete and re-run setup."
        return
    fi

    local jwt_secret admin_password
    jwt_secret=$(generate_secret)
    admin_password=$(generate_secret | head -c 16)

    cat > "$ENV_FILE" <<EOF
# Mosoro Environment Configuration
# Auto-generated by: make setup
# ============================================================================

# --- MQTT Broker ---
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=8883
MQTT_USE_TLS=true

# --- API Server ---
API_HOST=0.0.0.0
API_PORT=8000

# --- Authentication ---
JWT_SECRET=$jwt_secret
ADMIN_PASSWORD=$admin_password

# --- Robot Config ---
ROBOTS_YAML_PATH=./robots.yaml

# --- Logging ---
LOG_LEVEL=INFO
EOF

    info "Generated ${BOLD}.env${RESET} with auto-generated secrets"
    echo ""
    echo "  ${YELLOW}Important:${RESET} Your admin password is: ${BOLD}$admin_password${RESET}"
    echo "  ${DIM}(Save this — it won't be shown again)${RESET}"
}

# ---------------------------------------------------------------------------
# Offer to start the stack
# ---------------------------------------------------------------------------
offer_start() {
    step "Ready to Launch"
    echo ""
    echo "  Your configuration is complete!"
    echo ""
    echo "  ${BOLD}Next steps:${RESET}"
    echo "    1. Review ${BOLD}robots.yaml${RESET} and ${BOLD}.env${RESET}"
    echo "    2. Start the stack: ${BOLD}make up${RESET}"
    echo "    3. Open the dashboard: ${BOLD}http://localhost:3000${RESET}"
    echo ""

    read -rp "  Start the stack now? [y/N]: " start_now
    if [[ "$start_now" =~ ^[Yy] ]]; then
        echo ""
        info "Starting Mosoro..."
        cd "$PROJECT_DIR" && make up
    else
        echo ""
        info "Run ${BOLD}make up${RESET} when you're ready."
    fi
}

# ---------------------------------------------------------------------------
# Main — Full setup flow
# ---------------------------------------------------------------------------
main_setup() {
    banner
    check_prerequisites

    show_robot_catalog
    select_adapters
    install_adapters
    configure_robots
    generate_robots_yaml
    generate_env
    offer_start
}

# ---------------------------------------------------------------------------
# Main — Add robot flow (--add)
# ---------------------------------------------------------------------------
main_add_robot() {
    banner
    check_prerequisites

    echo "  ${DIM}Adding robot(s) to existing configuration${RESET}"

    show_robot_catalog
    select_adapters
    install_adapters
    configure_robots
    append_robots_yaml

    echo ""
    info "Done! Restart the stack to pick up changes: ${BOLD}make up${RESET}"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
case "${1:-}" in
    --add)
        main_add_robot
        ;;
    --help|-h)
        echo "Usage: $0 [--add]"
        echo ""
        echo "  (no args)   Full interactive setup"
        echo "  --add       Add another robot to existing config"
        exit 0
        ;;
    *)
        main_setup
        ;;
esac
