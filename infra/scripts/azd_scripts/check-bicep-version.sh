#!/bin/sh
# Pre-provision hook: Informs users about the minimum Bicep CLI version requirement.
# Displays the minimum Bicep version needed (>= 0.33.0) and provides steps
# to check, install, or upgrade Bicep via Azure CLI. Prompts the user to
# confirm before proceeding with deployment.

MIN_BICEP_VERSION="0.33.0"

printf "\n"
printf "\033[1;33m===============================================================\n"
printf "\033[0;32m BICEP VERSION CHECK\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"
printf "This accelerator requires Bicep CLI version >= %s.\n" "$MIN_BICEP_VERSION"
printf "\n"
printf "\033[1;33mPlease open a SEPARATE terminal to check and update your Bicep version,\n"
printf "then come back to THIS terminal to continue the deployment.\033[0m\n"
printf "\n"
printf "\033[0;36mSteps:\033[0m\n"
printf "  1. Check your current Bicep version:\n"
printf "       \033[0;36maz bicep version\033[0m\n"
printf "\n"
printf "  2. If Bicep is not installed, install it:\n"
printf "       \033[0;36maz bicep install\033[0m\n"
printf "\n"
printf "  3. If Bicep is installed but version is below %s, upgrade it:\n" "$MIN_BICEP_VERSION"
printf "       \033[0;36maz bicep upgrade\033[0m\n"
printf "\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"

while true; do
    printf "Do you want to proceed with deployment? (y/n): "
    read response

    case "$response" in
        y|Y)
            printf "\n"
            printf "\033[0;32mProceeding with deployment...\033[0m\n"
            exit 0
            ;;
        n|N)
            printf "\n"
            printf "\033[0;31mDeployment aborted by user.\033[0m\n"
            exit 1
            ;;
        *)
            printf "\033[1;33mInvalid input. Please enter 'y' or 'n'.\033[0m\n"
            ;;
    esac
done
