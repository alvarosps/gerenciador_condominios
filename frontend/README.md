# Frontend - Sistema de Gerenciamento de Condomínios

Este é o frontend da aplicação de gerenciamento de condomínios, desenvolvido com React + TypeScript + Vite e estilizado com **Tailwind CSS v4** e **Ant Design**.

## 🛠️ Tecnologias Utilizadas

- **React 19.1.0** - Biblioteca principal para construção da interface
- **TypeScript 5.8.3** - Superset do JavaScript com tipagem estática
- **Vite 6.3.5** - Build tool e dev server
- **Tailwind CSS 4.1.11** - Framework CSS utility-first
- **Ant Design 5.25.4** - Biblioteca de componentes React
- **React Router DOM 7.6.2** - Roteamento para aplicações React
- **Axios 1.9.0** - Cliente HTTP para requisições à API
- **Day.js 1.11.13** - Biblioteca para manipulação de datas

## 📦 Instalação e Execução

### Pré-requisitos
- Node.js 18+ 
- npm ou yarn

### Passos para executar

```bash
# Instalar dependências
npm install

# Executar em modo de desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview do build de produção
npm run preview
```

A aplicação estará disponível em `http://localhost:3000`

## 🎨 Estilização

### Tailwind CSS v4
A aplicação foi refatorada para usar a versão mais recente do Tailwind CSS (v4), que traz:

- **Nova sintaxe de configuração**: Usa `@theme` dentro do CSS em vez de arquivo de configuração JavaScript
- **Import simplificado**: `@import "tailwindcss"` em vez de múltiplas diretivas
- **Melhor performance**: Engine mais rápida e otimizada
- **Tipagem melhorada**: Melhor suporte para TypeScript

### Integração com Ant Design
- Mantém todos os componentes do Ant Design funcionais
- Customiza estilos do Ant Design usando classes do Tailwind
- Cores personalizadas definidas no tema para manter consistência
- Classes utilitárias do Tailwind para layouts responsivos e espaçamentos

### Cores Personalizadas
```css
/* Paleta primary baseada no azul do Ant Design */
--color-primary-50: #e6f7ff;
--color-primary-100: #bae7ff;
--color-primary-200: #91d5ff;
--color-primary-300: #69c0ff;
--color-primary-400: #40a9ff;
--color-primary-500: #1890ff;
--color-primary-600: #096dd9;
--color-primary-700: #0050b3;
--color-primary-800: #003a8c;
--color-primary-900: #002766;
```

## 📁 Estrutura do Projeto

```
frontend/
├── src/
│   ├── components/          # Componentes reutilizáveis
│   │   └── AppLayout.tsx    # Layout principal da aplicação
│   ├── pages/               # Páginas da aplicação
│   │   ├── Dashboard.tsx    # Dashboard principal
│   │   ├── Buildings.tsx    # Gestão de prédios
│   │   ├── Apartments.tsx   # Gestão de apartamentos
│   │   ├── Tenants.tsx      # Gestão de inquilinos
│   │   ├── Leases.tsx       # Gestão de contratos
│   │   └── Furnitures.tsx   # Gestão de móveis
│   ├── hooks/               # Hooks personalizados
│   │   └── useApi.ts        # Hook para chamadas da API
│   ├── services/            # Serviços e configurações
│   │   └── api.ts          # Configuração do Axios
│   ├── types/               # Definições de tipos TypeScript
│   │   └── index.ts        # Tipos principais
│   ├── utils/               # Utilitários e helpers
│   │   └── formatters.ts   # Formatadores de dados
│   ├── App.tsx             # Componente principal
│   ├── App.css             # Estilos globais e Tailwind
│   └── main.tsx            # Ponto de entrada da aplicação
├── postcss.config.js       # Configuração do PostCSS
├── tsconfig.json           # Configuração do TypeScript
├── vite.config.ts          # Configuração do Vite
└── package.json            # Dependências e scripts
```

## 🚀 Funcionalidades Implementadas

### Dashboard
- **Estatísticas em cards**: Exibição de métricas importantes com ícones
- **Atividades recentes**: Timeline de eventos do sistema
- **Ações rápidas**: Botões para principais funcionalidades
- **Layout responsivo**: Adaptável a diferentes tamanhos de tela

### Layout Principal
- **Sidebar navegável**: Menu lateral com todas as seções
- **Header responsivo**: Título da aplicação e controle de sidebar
- **Conteúdo principal**: Área de trabalho para cada página

## 📱 Responsividade

A aplicação é totalmente responsiva, usando:

- **Grid system do Ant Design**: Para layouts estruturados
- **Classes utilitárias do Tailwind**: Para ajustes finos
- **Breakpoints padrão**:
  - `xs`: < 576px (celulares)
  - `sm`: ≥ 576px (celulares grandes)
  - `md`: ≥ 768px (tablets)
  - `lg`: ≥ 992px (desktops)
  - `xl`: ≥ 1200px (telas grandes)

## 🎯 Próximos Passos

1. **Implementar páginas restantes**: Buildings, Apartments, Tenants, Leases, Furnitures
2. **Conectar com API backend**: Integração com Django REST API
3. **Adicionar formulários**: Criação e edição de entidades
4. **Implementar autenticação**: Login e controle de acesso
5. **Testes unitários**: Jest + React Testing Library
6. **Documentação de componentes**: Storybook

## 🤝 Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📝 Convenções de Código

- **Components**: PascalCase (ex: `AppLayout.tsx`)
- **Files**: camelCase (ex: `useApi.ts`)
- **CSS Classes**: Usar classes do Tailwind sempre que possível
- **Types**: Definir tipos TypeScript explícitos
- **Imports**: Organizar imports por categoria (libs, components, utils) 