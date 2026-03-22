#!/bin/bash
# space-hog demo — fast version, skip slow scans

echo "→ Installing space-hog (zero dependencies)"
sleep 0.5
echo "$ pip install space-hog"
sleep 0.3
echo "Successfully installed space-hog-0.5.0"
sleep 0.8

echo ""
echo "→ What can I clean up? (prioritized by safety)"
echo "$ space-hog --advise 2>&1 | head -35"
sleep 0.5
space-hog --advise 2>&1 | head -35
sleep 2

echo ""
echo "→ Cleanup stats"
echo "$ space-hog --stats"
sleep 0.5
space-hog --stats 2>&1
sleep 1.5
