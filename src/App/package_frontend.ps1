mkdir dist -Force
rm dist/* -r -Force

# Python
cp requirements.txt dist -Force
cp *.py dist -Force

# Node
npm install
npm run build
cp -r build dist -Force