#!/bin/bash
echo "Testing local API endpoints..."

echo "Testing root endpoint:"
curl -s http://localhost:8000/ | jq '.'
echo

echo "Testing /api endpoint:"
curl -s http://localhost:8000/api | jq '.'
echo

echo "Testing /api/health endpoint:"
curl -s http://localhost:8000/api/health | jq '.'
echo

echo "All tests completed." 