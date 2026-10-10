#!/bin/bash
#
# Wifite2 Cracked Database Cleaner
# Advanced duplicate detection and removal for cracked.json
#
# Detects and removes:
#  - Duplicate BSSIDs (same MAC address)
#  - Duplicate ESSID+Key combinations (same network credentials)
#  - ESSID variations (hex encoding, unicode, trailing spaces)
#  - Invalid/corrupted entries
#
# Usage: ./clean.sh [cracked.json] [--aggressive]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Parse arguments
CRACKED_FILE=""
AGGRESSIVE_MODE=false

for arg in "$@"; do
    case $arg in
        --aggressive)
            AGGRESSIVE_MODE=true
            shift
            ;;
        *)
            if [ -z "$CRACKED_FILE" ]; then
                CRACKED_FILE="$arg"
            fi
            ;;
    esac
done

# Default file location (relative to tools directory)
CRACKED_FILE="${CRACKED_FILE:-../cracked.json}"

# Banner
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Wifite2 Cracked Database Cleaner v2.0        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check if file exists
if [ ! -f "$CRACKED_FILE" ]; then
    echo -e "${RED}[!]${NC} Error: File '$CRACKED_FILE' not found"
    echo -e "${BLUE}[?]${NC} Usage: $0 [cracked.json] [--aggressive]"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}[!]${NC} Error: 'jq' is required but not installed"
    echo -e "${BLUE}[?]${NC} Install with: sudo apt install jq"
    exit 1
fi

# Validate JSON format
if ! jq empty "$CRACKED_FILE" 2>/dev/null; then
    echo -e "${RED}[!]${NC} Error: '$CRACKED_FILE' is not valid JSON"
    exit 1
fi

# Create backup
BACKUP_FILE="${CRACKED_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CRACKED_FILE" "$BACKUP_FILE"
echo -e "${GREEN}[+]${NC} Created backup: $BACKUP_FILE"

# Count original entries
ORIGINAL_COUNT=$(jq 'length' "$CRACKED_FILE")
echo -e "${BLUE}[*]${NC} Original entries: $ORIGINAL_COUNT"
echo ""

# ============================================================================
# PHASE 1: Normalize ESSID fields (fix encoding issues)
# ============================================================================
echo -e "${MAGENTA}[Phase 1]${NC} Normalizing ESSID encoding..."

jq 'map(
    . + {
        essid: (
            .essid 
            | gsub("\\u0011\\u0011\\u0011"; "111111")  # Fix unicode encoding
            | gsub("^\\s+|\\s+$"; "")                   # Trim whitespace
        )
    }
)' "$CRACKED_FILE" > "${CRACKED_FILE}.phase1"

PHASE1_CHANGES=$(jq -r '
    [.[] | select(.essid != (.essid | gsub("\\u0011\\u0011\\u0011"; "111111") | gsub("^\\s+|\\s+$"; "")))] | length
' "$CRACKED_FILE")

if [ "$PHASE1_CHANGES" -gt 0 ]; then
    echo -e "${YELLOW}  →${NC} Normalized $PHASE1_CHANGES ESSID(s)"
else
    echo -e "${GREEN}  ✓${NC} No normalization needed"
fi

# ============================================================================
# PHASE 2: Remove duplicate BSSIDs (keep most recent)
# ============================================================================
echo -e "${MAGENTA}[Phase 2]${NC} Removing duplicate BSSIDs..."

# Find duplicates before removal
BSSID_DUPS=$(jq -r '[.[].bssid] | group_by(.) | map(select(length > 1)) | length' "${CRACKED_FILE}.phase1")

# Remove duplicates, keeping most recent
jq 'sort_by(.date) | reverse | unique_by(.bssid)' "${CRACKED_FILE}.phase1" > "${CRACKED_FILE}.phase2"

PHASE2_REMOVED=$(($(jq 'length' "${CRACKED_FILE}.phase1") - $(jq 'length' "${CRACKED_FILE}.phase2")))

if [ "$PHASE2_REMOVED" -gt 0 ]; then
    echo -e "${YELLOW}  →${NC} Removed $PHASE2_REMOVED duplicate BSSID(s) from $BSSID_DUPS network(s)"
    
    # Show which BSSIDs had duplicates
    jq -r '.[].bssid' "${CRACKED_FILE}.phase1" | sort | uniq -d | head -10 | while read -r bssid; do
        ESSID=$(jq -r ".[] | select(.bssid == \"$bssid\") | .essid" "${CRACKED_FILE}.phase2" | head -1)
        COUNT=$(jq -r ".[] | select(.bssid == \"$bssid\") | .bssid" "${CRACKED_FILE}.phase1" | wc -l)
        echo -e "${CYAN}     •${NC} $bssid ($ESSID) - had $COUNT entries"
    done
    
    # Show if there are more
    TOTAL_DUP_BSSIDS=$(jq -r '.[].bssid' "${CRACKED_FILE}.phase1" | sort | uniq -d | wc -l)
    if [ "$TOTAL_DUP_BSSIDS" -gt 10 ]; then
        echo -e "${CYAN}     •${NC} ... and $((TOTAL_DUP_BSSIDS - 10)) more"
    fi
else
    echo -e "${GREEN}  ✓${NC} No duplicate BSSIDs found"
fi

# ============================================================================
# PHASE 3: Remove duplicate ESSID+Key combinations (aggressive mode)
# ============================================================================
if [ "$AGGRESSIVE_MODE" = true ]; then
    echo -e "${MAGENTA}[Phase 3]${NC} Removing duplicate ESSID+Key combinations..."
    
    # Find duplicates before removal
    ESSID_KEY_DUPS=$(jq -r '
        [.[] | select(.key != null) | "\(.essid)|\(.key)"] 
        | group_by(.) 
        | map(select(length > 1)) 
        | length
    ' "${CRACKED_FILE}.phase2")
    
    # Remove duplicates based on ESSID+Key, keeping most recent
    jq 'sort_by(.date) | reverse | unique_by("\(.essid)|\(.key // "null")")' "${CRACKED_FILE}.phase2" > "${CRACKED_FILE}.phase3"
    
    PHASE3_REMOVED=$(($(jq 'length' "${CRACKED_FILE}.phase2") - $(jq 'length' "${CRACKED_FILE}.phase3")))
    
    if [ "$PHASE3_REMOVED" -gt 0 ]; then
        echo -e "${YELLOW}  →${NC} Removed $PHASE3_REMOVED duplicate ESSID+Key combination(s)"
        
        # Show examples
        jq -r '.[] | select(.key != null) | "\(.essid)|\(.key)"' "${CRACKED_FILE}.phase2" | \
            sort | uniq -d | head -5 | while IFS='|' read -r essid key; do
            COUNT=$(jq -r ".[] | select(.essid == \"$essid\" and .key == \"$key\") | .bssid" "${CRACKED_FILE}.phase2" | wc -l)
            echo -e "${CYAN}     •${NC} $essid / $key - had $COUNT different BSSIDs"
        done
    else
        echo -e "${GREEN}  ✓${NC} No duplicate ESSID+Key combinations found"
    fi
else
    echo -e "${MAGENTA}[Phase 3]${NC} Skipped (use --aggressive to enable ESSID+Key deduplication)"
    cp "${CRACKED_FILE}.phase2" "${CRACKED_FILE}.phase3"
    PHASE3_REMOVED=0
fi

# ============================================================================
# PHASE 4: Remove invalid entries
# ============================================================================
echo -e "${MAGENTA}[Phase 4]${NC} Removing invalid entries..."

# Remove entries with missing required fields
jq '[.[] | select(
    .type != null and 
    .date != null and 
    .essid != null and 
    .bssid != null and
    .bssid != "" and
    .essid != ""
)]' "${CRACKED_FILE}.phase3" > "${CRACKED_FILE}.phase4"

PHASE4_REMOVED=$(($(jq 'length' "${CRACKED_FILE}.phase3") - $(jq 'length' "${CRACKED_FILE}.phase4")))

if [ "$PHASE4_REMOVED" -gt 0 ]; then
    echo -e "${YELLOW}  →${NC} Removed $PHASE4_REMOVED invalid/incomplete entry(ies)"
else
    echo -e "${GREEN}  ✓${NC} No invalid entries found"
fi

# ============================================================================
# PHASE 5: Sort by date (newest first) and finalize
# ============================================================================
echo -e "${MAGENTA}[Phase 5]${NC} Sorting and finalizing..."

jq 'sort_by(.date) | reverse' "${CRACKED_FILE}.phase4" > "${CRACKED_FILE}.final"

# ============================================================================
# Summary and Statistics
# ============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Cleanup Summary                               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"

FINAL_COUNT=$(jq 'length' "${CRACKED_FILE}.final")
TOTAL_REMOVED=$((ORIGINAL_COUNT - FINAL_COUNT))

echo -e "${BLUE}[*]${NC} Original entries:     $ORIGINAL_COUNT"
echo -e "${BLUE}[*]${NC} Final entries:        $FINAL_COUNT"
echo -e "${BLUE}[*]${NC} Total removed:        $TOTAL_REMOVED"
echo ""
echo -e "${BLUE}[*]${NC} Breakdown:"
echo -e "    ${CYAN}•${NC} ESSID normalized:     $PHASE1_CHANGES"
echo -e "    ${CYAN}•${NC} Duplicate BSSIDs:     $PHASE2_REMOVED"
echo -e "    ${CYAN}•${NC} Duplicate ESSID+Key:  $PHASE3_REMOVED"
echo -e "    ${CYAN}•${NC} Invalid entries:      $PHASE4_REMOVED"
echo ""

# Statistics
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Database Statistics                           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"

# Count by type
echo -e "${BLUE}[*]${NC} Entries by attack type:"
jq -r '[.[] | .type] | group_by(.) | map({type: .[0], count: length}) | .[] | "    \(.type): \(.count)"' "${CRACKED_FILE}.final"

echo ""
echo -e "${BLUE}[*]${NC} Unique networks (ESSID): $(jq -r '[.[].essid] | unique | length' "${CRACKED_FILE}.final")"
echo -e "${BLUE}[*]${NC} Unique access points (BSSID): $(jq -r '[.[].bssid] | unique | length' "${CRACKED_FILE}.final")"
echo -e "${BLUE}[*]${NC} Networks with passwords: $(jq -r '[.[] | select(.key != null)] | length' "${CRACKED_FILE}.final")"

# Top 5 most common passwords
echo ""
echo -e "${BLUE}[*]${NC} Top 5 most common passwords:"
jq -r '[.[] | select(.key != null) | .key] | group_by(.) | map({key: .[0], count: length}) | sort_by(.count) | reverse | .[0:5] | .[] | "    \(.count)x - \(.key)"' "${CRACKED_FILE}.final"

# ============================================================================
# Finalize
# ============================================================================
echo ""

if [ "$TOTAL_REMOVED" -gt 0 ]; then
    mv "${CRACKED_FILE}.final" "$CRACKED_FILE"
    echo -e "${GREEN}[+]${NC} Successfully cleaned $CRACKED_FILE"
    echo -e "${GREEN}[+]${NC} Removed $TOTAL_REMOVED duplicate/invalid entries"
else
    echo -e "${GREEN}[+]${NC} Database is already clean - no changes needed"
    rm "${CRACKED_FILE}.final"
fi

# Cleanup temporary files
rm -f "${CRACKED_FILE}.phase"* 2>/dev/null

echo -e "${BLUE}[*]${NC} Backup saved as: $BACKUP_FILE"
echo -e "${GREEN}[✓]${NC} Done!"
echo ""
