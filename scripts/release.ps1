param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must match semantic versioning like 1.0.0"
}

$tag = "v$Version"

git diff --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Working tree has uncommitted changes. Commit or stash them before tagging a release."
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Index has staged but uncommitted changes. Commit them before tagging a release."
}

git fetch --tags origin
if ($LASTEXITCODE -ne 0) {
    throw "Failed to fetch tags from origin."
}

$existingTag = git tag --list $tag
if ($LASTEXITCODE -ne 0) {
    throw "Failed to query existing tags."
}
if ($existingTag) {
    throw "Tag $tag already exists."
}

git tag -a $tag -m "Release $tag"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create tag $tag."
}

git push origin $tag
if ($LASTEXITCODE -ne 0) {
    throw "Failed to push tag $tag."
}

Write-Host "Pushed $tag."
Write-Host "GitHub Actions will run tests, build release artifacts, render the user guide and API PDFs, publish the GitHub Release, and upload Python distributions to PyPI."
Write-Host "If release-notes/$tag.md exists in the repository, that file will be used as the release body."
