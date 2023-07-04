#!/usr/bin/env bash
script_folder="$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)"
workspaces_folder="$(cd "${script_folder}/../.." && pwd)"

clone-repo()
{
    cd "${workspaces_folder}"
    if [ ! -d "${1#*/}" ]; then
        git clone "https://github.com/$1"
    else
        echo "Already cloned $1"
    fi
}

if [ "${CODESPACES}" = "true" ]; then
    # Remove the default credential helper
    sudo sed -i -E 's/helper =.*//' /etc/gitconfig

    # Add one that just uses secrets available in the Codespace
    git config --global credential.helper '!f() { sleep 1; echo "username=${GITHUB_USER}"; echo "password=${GH_TOKEN}"; }; f'
fi

repositories=('alphagov/notifications-api' 'alphagov/notifications-template-preview' 'alphagov/document-download-api' 'alphagov/document-download-frontend' 'alphagov/notifications-local' 'alphagov/notifications-antivirus')
for repository in ${repositories[@]}; do
    clone-repo "$repository"
done
