#!/usr/bin/env node

/**
 * Generate TypeScript types from OpenAPI schema
 *
 * This script fetches the OpenAPI schema from the Django backend
 * and generates TypeScript types and API client code.
 *
 * Usage:
 *   npm run generate-types
 *   npm run generate-types -- --url http://custom-backend/api/schema/
 */

const { generate } = require('openapi-typescript-codegen');
const path = require('path');

// Configuration
const config = {
  // OpenAPI schema URL (can be overridden via --url argument)
  input: process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL}/schema/`
    : 'http://localhost:8000/api/schema/',

  // Output directory for generated files
  output: path.join(__dirname, '../lib/api/generated'),

  // Use fetch instead of axios for the generated client
  httpClient: 'fetch',

  // Use interfaces instead of types
  useOptions: true,
  useUnionTypes: true,
  exportCore: true,
  exportServices: true,
  exportModels: true,
  exportSchemas: false,

  // Indentation
  indent: '  ',

  // Postfix for services
  postfixServices: 'Service',

  // Postfix for models
  postfixModels: '',

  // Use single quotes
  useSingleQuote: true,

  // Client name
  clientName: 'ApiClient',
};

// Check for custom URL argument
const urlArgIndex = process.argv.indexOf('--url');
if (urlArgIndex !== -1 && process.argv[urlArgIndex + 1]) {
  config.input = process.argv[urlArgIndex + 1];
}

console.log('🔄 Generating TypeScript types from OpenAPI schema...');
console.log(`📡 Fetching schema from: ${config.input}`);
console.log(`📁 Output directory: ${config.output}`);

generate(config)
  .then(() => {
    console.log('✅ TypeScript types generated successfully!');
    console.log('');
    console.log('Generated files:');
    console.log('  - lib/api/generated/models/     (TypeScript interfaces)');
    console.log('  - lib/api/generated/services/   (API service classes)');
    console.log('  - lib/api/generated/core/       (Core utilities)');
    console.log('  - lib/api/generated/index.ts    (Main export file)');
    console.log('');
    console.log('💡 Import types: import { Building, Apartment } from "@/lib/api/generated"');
  })
  .catch((error) => {
    console.error('❌ Failed to generate types:', error.message);
    console.error('');
    console.error('Troubleshooting:');
    console.error('  1. Make sure the backend is running at:', config.input);
    console.error('  2. Check that the OpenAPI schema endpoint is accessible');
    console.error('  3. Verify CORS is configured on the backend');
    console.error('  4. Try accessing the schema in your browser:', config.input);
    process.exit(1);
  });
