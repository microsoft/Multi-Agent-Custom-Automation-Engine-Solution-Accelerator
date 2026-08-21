mkdir dist -Force
rm dist/* -r -Force

# Python
cp requirements.txt dist -Force
cp *.py dist -Force

# Node
$npmInstallStart = Get-Date
npm install
$npmInstallEnd = Get-Date
Write-Host "npm install duration: $(($npmInstallEnd - $npmInstallStart).TotalSeconds)s"
npm run build
cp -r build dist -Force