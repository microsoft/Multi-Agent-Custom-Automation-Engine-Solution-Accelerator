#!/bin/sh
# Pre-provision hook: Checks Bicep CLI version and offers to update if outdated.
# Automatically detects the installed Bicep CLI version via Azure CLI,
# compares against the minimum required version (0.33.0), and offers
# to install or upgrade if needed.

MIN_BICEP_VERSION="0.33.0"

# Compare two semver strings. Returns 0 if equal, 1 if first > second, 2 if first < second.
compare_semver() {
    current_major=$(echo "$1" | cut -d. -f1)
    current_minor=$(echo "$1" | cut -d. -f2)
    current_patch=$(echo "$1" | cut -d. -f3)
    min_major=$(echo "$2" | cut -d. -f1)
    min_minor=$(echo "$2" | cut -d. -f2)
    min_patch=$(echo "$2" | cut -d. -f3)

    if [ "$current_major" -gt "$min_major" ]; then return 0; fi
    if [ "$current_major" -lt "$min_major" ]; then return 2; fi
    if [ "$current_minor" -gt "$min_minor" ]; then return 0; fi
    if [ "$current_minor" -lt "$min_minor" ]; then return 2; fi
    if [ "$current_patch" -ge "$min_patch" ]; then return 0; fi
    return 2
}

printf "\n"
printf "\033[1;33m===============================================================\n"
printf "\033[0;32m BICEP VERSION CHECK\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"

# Attempt to get Bicep version
bicep_output=$(az bicep version 2>&1)
bicep_exit_code=$?

if [ $bicep_exit_code -ne 0 ] || [ -z "$bicep_output" ]; then
    printf "\033[0;31mBicep CLI is not installed.\033[0m\n"
    printf "This accelerator requires Bicep CLI version >= %s.\n" "$MIN_BICEP_VERSION"
    printf "\n"

    while true; do
        printf "Would you like us to install Bicep CLI? (y/n): "
        read response
        case "$response" in
            y|Y)
                printf "\n"
                printf "\033[0;36mInstalling Bicep CLI...\033[0m\n"
                az bicep install
                if [ $? -ne 0 ]; then
                    printf "\033[0;31mFailed to install Bicep CLI. Please install manually: az bicep install\033[0m\n"
                    exit 1
                fi
                printf "\033[0;32mBicep CLI installed successfully.\033[0m\n"
                exit 0
                ;;
            n|N)
                printf "\n"
                printf "\033[0;31mBicep CLI >= %s is required. Deployment aborted.\033[0m\n" "$MIN_BICEP_VERSION"
                exit 1
                ;;
            *)
                printf "\033[1;33mInvalid input. Please enter 'y' or 'n'.\033[0m\n"
                ;;
        esac
    done
fi

# Parse version from the "Bicep CLI version X.Y.Z" line (ignore upgrade notice line)
current_version=$(echo "$bicep_output" | grep 'Bicep CLI version' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

if [ -z "$current_version" ]; then
    printf "\033[0;31mCould not parse Bicep version from output: %s\033[0m\n" "$bicep_output"
    printf "\033[1;33mPlease check your Bicep installation manually.\033[0m\n"
    exit 1
fi

compare_semver "$current_version" "$MIN_BICEP_VERSION"
result=$?

if [ $result -eq 0 ]; then
    printf "\033[0;32mBicep CLI version %s detected. Meets minimum requirement (>= %s).\033[0m\n" "$current_version" "$MIN_BICEP_VERSION"
    printf "\n"
    exit 0
fi

# Version is below minimum
printf "\033[1;33mBicep CLI version %s detected.\033[0m\n" "$current_version"
printf "This accelerator requires Bicep CLI version >= %s.\n" "$MIN_BICEP_VERSION"
printf "\n"

while true; do
    printf "Would you like us to upgrade Bicep CLI? (y/n): "
    read response
    case "$response" in
        y|Y)
            printf "\n"
            printf "\033[0;36mUpgrading Bicep CLI...\033[0m\n"
            az bicep upgrade
            if [ $? -ne 0 ]; then
                printf "\033[0;31mFailed to upgrade Bicep CLI. Please upgrade manually: az bicep upgrade\033[0m\n"
                exit 1
            fi
            printf "\033[0;32mBicep CLI upgraded successfully.\033[0m\n"
            exit 0
            ;;
        n|N)
            printf "\n"
            printf "\033[0;31mBicep CLI >= %s is required. Deployment aborted.\033[0m\n" "$MIN_BICEP_VERSION"
            exit 1
            ;;
        *)
            printf "\033[1;33mInvalid input. Please enter 'y' or 'n'.\033[0m\n"
            ;;
    esac
done
