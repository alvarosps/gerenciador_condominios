# Advanced Features Implementation - Phase 8

This document provides comprehensive documentation for the advanced features implemented in Phase 8 of the Condomínios Manager project.

## 🚀 Features Overview

### 1. Global Search System
- **Location**: `src/components/GlobalSearch/`
- **Features**:
  - Search across all entities (buildings, apartments, tenants, leases, furniture)
  - Search history with localStorage persistence
  - Intelligent result categorization
  - Real-time search with debouncing
  - Keyboard navigation support

### 2. Advanced Filtering System
- **Location**: `src/components/AdvancedFilters/`
- **Features**:
  - Dynamic filter builder with multiple field types
  - Filter presets with save/load functionality
  - Support for text, number, date, boolean, and select filters
  - Complex operators (contains, equals, between, etc.)
  - Filter combinations with AND logic

### 3. Bulk Operations Framework
- **Location**: `src/components/BulkOperations/` & `src/hooks/useBulkOperations.ts`
- **Features**:
  - Multi-selection with checkboxes
  - Bulk delete with confirmation
  - Bulk update operations
  - Bulk export to CSV/Excel
  - Custom bulk actions
  - Progress tracking and error handling

### 4. Notification Center
- **Location**: `src/components/NotificationCenter/`
- **Features**:
  - Real-time notification system
  - Multiple notification types (info, success, warning, error)
  - Notification persistence and history
  - Custom actions on notifications
  - Desktop notifications support
  - Priority levels and categorization

### 5. File Management System
- **Location**: `src/components/FileManager/` & `src/hooks/useFileManager.ts`
- **Features**:
  - Drag & drop file upload
  - File validation by type and size
  - Image preview and document handling
  - Progress tracking for uploads
  - File organization by categories
  - Document templates support

## 📦 Installation & Setup

### Prerequisites
```bash
npm install xlsx dayjs
npm install @types/xlsx --save-dev
```

### Required Dependencies
The following are already included in the project:
- `antd` - UI components
- `react-router-dom` - Navigation
- `dayjs` - Date handling
- `xlsx` - Excel export functionality

## 🔧 Integration Guide

### 1. Global Search Integration

Add to your main layout (already implemented in `AppLayout.tsx`):

```tsx
import { GlobalSearch } from './components/GlobalSearch';

// In your header component
<GlobalSearch className="mr-4" />
```

### 2. Enhanced Data Table Integration

Replace existing DataTable with EnhancedDataTable:

```tsx
import { EnhancedDataTable } from './components/common';
import { FilterFieldConfig } from './components/AdvancedFilters';
import { BulkAction } from './components/BulkOperations';

// Define filter fields
const filterFields: FilterFieldConfig[] = [
  {
    field: 'name',
    label: 'Nome',
    type: 'text',
    config: { placeholder: 'Digite o nome...' }
  },
  {
    field: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'active', label: 'Ativo' },
      { value: 'inactive', label: 'Inativo' }
    ]
  }
];

// Define bulk actions
const bulkActions: BulkAction[] = [
  {
    key: 'activate',
    label: 'Ativar Items',
    icon: <PlayCircleOutlined />
  },
  {
    key: 'update_status',
    label: 'Atualizar Status',
    requiresInput: true,
    inputConfig: {
      type: 'select',
      label: 'Novo Status',
      options: [
        { value: 'active', label: 'Ativo' },
        { value: 'inactive', label: 'Inativo' }
      ]
    }
  }
];

// Use in component
<EnhancedDataTable
  data={data}
  columns={columns}
  enableAdvancedFilters={true}
  filterFields={filterFields}
  enableBulkOperations={true}
  bulkActions={bulkActions}
  onBulkDelete={handleBulkDelete}
  onBulkUpdate={handleBulkUpdate}
  onBulkAction={handleBulkAction}
  exportEntityType="building" // or apartment, tenant, lease, furniture
  onCreateNew={handleCreate}
/>
```

### 3. Notification System Integration

Wrap your app with NotificationProvider (already implemented):

```tsx
import { NotificationProvider, useNotifications } from './components/NotificationCenter';

// In your App.tsx
<NotificationProvider>
  <YourAppContent />
</NotificationProvider>

// In components
const { showSuccess, showError, addNotification } = useNotifications();

// Show simple notification
showSuccess('Success!', 'Operation completed successfully');

// Show notification with actions
addNotification(
  'New Task',
  'You have a new task pending approval',
  {
    type: 'info',
    priority: 'high',
    actions: [
      {
        id: 'approve',
        label: 'Approve',
        action: () => handleApprove()
      }
    ]
  }
);
```

### 4. File Management Integration

```tsx
import { FileUpload } from './components/FileManager';

// In your component
<FileUpload
  category="document" // or image, contract, tenant_document, apartment_media
  title="Upload Documents"
  description="Upload PDFs, Word docs, and images"
  maxFiles={10}
  autoUpload={true}
  onUpload={handleFileUpload}
  onRemove={handleFileRemove}
/>

// Upload handler
const handleFileUpload = async (file) => {
  // Your upload logic here
  return {
    url: 'https://your-server.com/uploads/file.pdf',
    metadata: { uploadedAt: new Date().toISOString() }
  };
};
```

### 5. Bulk Operations Integration

```tsx
import { useBulkOperations } from './hooks/useBulkOperations';
import { BulkOperationsToolbar } from './components/BulkOperations';

const bulkOps = useBulkOperations({
  onBulkDelete: async (ids) => {
    // Delete items by IDs
    await deleteItems(ids);
    return { success: ids.length, failed: 0, errors: [] };
  },
  onBulkExport: async (ids, format) => {
    // Export selected items
    await exportItems(ids, format);
  }
});

// In your render
{bulkOps.hasSelection() && (
  <BulkOperationsToolbar
    selectedCount={bulkOps.getSelectedCount()}
    totalCount={totalItems}
    isVisible={true}
    onDelete={bulkOps.bulkDelete}
    onExport={bulkOps.bulkExport}
    onClose={bulkOps.clearSelection}
  />
)}
```

## 🎯 Usage Examples

### Complete Page Integration Example

See `src/pages/Buildings/EnhancedBuildings.tsx` for a complete implementation example that includes:
- Enhanced data table with all features
- Advanced filtering
- Bulk operations
- File management
- Notifications integration

### Feature Showcase

Visit `src/components/common/FeatureShowcase.tsx` for an interactive demonstration of all features.

## 🔍 Filter Types Reference

### Text Filters
```tsx
{
  field: 'name',
  label: 'Name',
  type: 'text',
  config: {
    placeholder: 'Enter name...'
  }
}
```

### Number Range Filters
```tsx
{
  field: 'price',
  label: 'Price Range',
  type: 'numberRange',
  config: {
    min: 0,
    max: 1000,
    step: 10
  }
}
```

### Date Filters
```tsx
{
  field: 'createdAt',
  label: 'Created Date',
  type: 'date',
  config: {
    format: 'DD/MM/YYYY'
  }
}
```

### Select Filters
```tsx
{
  field: 'category',
  label: 'Category',
  type: 'select',
  options: [
    { value: 'A', label: 'Category A' },
    { value: 'B', label: 'Category B' }
  ],
  config: {
    allowClear: true,
    showSearch: true
  }
}
```

## 📊 Export Configuration

### Entity-Specific Export Columns

The system includes pre-configured export columns for each entity type:

```tsx
// Buildings
exportEntityType="building"

// Apartments  
exportEntityType="apartment"

// Tenants
exportEntityType="tenant"

// Leases
exportEntityType="lease"

// Furniture
exportEntityType="furniture"
```

### Custom Export Columns

```tsx
import { exportData, ExportColumn } from './utils/bulkExport';

const customColumns: ExportColumn[] = [
  {
    key: 'name',
    title: 'Name',
    dataIndex: 'name'
  },
  {
    key: 'status',
    title: 'Status',
    dataIndex: 'status',
    render: (value) => value === 'active' ? 'Ativo' : 'Inativo'
  }
];

await exportData(data, 'csv', {
  filename: 'custom_export',
  columns: customColumns
});
```

## 🔧 File Categories Configuration

### Available Categories

- `document` - General documents (PDF, Word, Excel, text)
- `image` - Images (JPG, PNG, GIF, WebP, SVG)
- `contract` - Contracts and legal documents (PDF, Word)
- `tenant_document` - Tenant personal documents
- `apartment_media` - Apartment photos and media

### Custom File Validation

```tsx
import { validateFile, FileValidationConfig } from './utils/fileValidation';

const customConfig: FileValidationConfig = {
  maxSizeBytes: 5 * 1024 * 1024, // 5MB
  allowedTypes: ['application/pdf', 'image/jpeg'],
  allowedExtensions: ['.pdf', '.jpg', '.jpeg'],
  requireDocument: true
};

const result = await validateFile(file, customConfig);
```

## 🚨 Error Handling

### Bulk Operations Error Handling

```tsx
const handleBulkDelete = async (ids: string[]) => {
  try {
    const results = await Promise.allSettled(
      ids.map(id => deleteItem(id))
    );
    
    const succeeded = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;
    
    return {
      success: succeeded,
      failed: failed,
      errors: results
        .filter(r => r.status === 'rejected')
        .map(r => (r as PromiseRejectedResult).reason.message)
    };
  } catch (error) {
    throw new Error('Bulk delete failed');
  }
};
```

### File Upload Error Handling

```tsx
const handleFileUpload = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file.file);
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error('Upload failed');
    }
    
    const data = await response.json();
    return { url: data.url, metadata: data.metadata };
  } catch (error) {
    throw new Error(`Upload failed: ${error.message}`);
  }
};
```

## 🔒 Security Considerations

### File Upload Security

- All file names are sanitized to prevent path traversal
- File types are validated both by extension and MIME type
- File size limits are enforced
- Dangerous file types are blocked by default

### Input Sanitization

```tsx
import { sanitizeFileName } from './utils/fileValidation';

const safeFileName = sanitizeFileName(originalFileName);
```

## 🎨 Customization

### Theme Customization

All components use Ant Design theming. Customize via ConfigProvider:

```tsx
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#1890ff',
      borderRadius: 8,
    },
  }}
>
  <App />
</ConfigProvider>
```

### Component Styling

Components include CSS-in-JS styling that can be overridden:

```tsx
<EnhancedDataTable
  className="custom-table"
  // ... other props
/>

// Custom CSS
.custom-table .ant-table-tbody > tr:hover > td {
  background-color: #f0f9ff;
}
```

## 📱 Responsive Design

All components are responsive and work on mobile devices:

- Global search adapts to smaller screens
- Filter panels collapse on mobile
- Bulk operations toolbar stacks on mobile
- File upload areas resize appropriately

## 🧪 Testing

### Component Testing

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationProvider } from './components/NotificationCenter';
import { EnhancedDataTable } from './components/common';

test('bulk operations work correctly', async () => {
  render(
    <NotificationProvider>
      <EnhancedDataTable
        data={testData}
        columns={testColumns}
        enableBulkOperations={true}
        onBulkDelete={mockBulkDelete}
      />
    </NotificationProvider>
  );
  
  // Test bulk selection
  const checkboxes = screen.getAllByRole('checkbox');
  fireEvent.click(checkboxes[1]); // Select first item
  
  // Test bulk delete
  const deleteButton = screen.getByText('Excluir');
  fireEvent.click(deleteButton);
  
  expect(mockBulkDelete).toHaveBeenCalledWith(['1']);
});
```

## 🔄 Performance Optimizations

### Virtualization

For large datasets, consider using virtual scrolling:

```tsx
<EnhancedDataTable
  virtual={true}
  scroll={{ y: 400 }}
  // ... other props
/>
```

### Debouncing

All search inputs use debouncing to prevent excessive API calls:

```tsx
const debouncedSearch = useDebounce(searchTerm, 300);
```

### Memoization

Components use React.memo and useMemo for optimal performance:

```tsx
const memoizedColumns = useMemo(() => generateColumns(), [dependencies]);
```

## 🤝 Contributing

When adding new features:

1. Follow existing patterns and component structure
2. Add proper TypeScript interfaces
3. Include error handling and loading states
4. Add responsive design considerations
5. Update documentation

## 📝 Changelog

### Phase 8 Implementation (Current)
- ✅ Global Search System
- ✅ Advanced Filtering System  
- ✅ Bulk Operations Framework
- ✅ Notification Center
- ✅ File Management System
- ✅ Enhanced Data Table Integration
- ✅ Complete Documentation

### Future Enhancements (Phase 9+)
- [ ] Real-time collaboration
- [ ] Advanced reporting
- [ ] Mobile app integration
- [ ] API integration improvements
- [ ] Performance monitoring

---

For questions or support, please refer to the project documentation or contact the development team.