import {
  ApartmentOutlined,
  BuildOutlined,
  FileTextOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Statistic } from 'antd';
import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          Dashboard
        </h1>
        <p className="text-gray-600">
          Visão geral do sistema de gerenciamento de condomínios
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="dashboard-stats">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              bordered={false} 
              className="bg-gradient-to-br from-blue-50 to-blue-100 hover:shadow-md transition-shadow duration-200"
            >
              <Statistic
                title="Total de Prédios"
                value={5}
                prefix={<BuildOutlined className="text-blue-500" />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              bordered={false}
              className="bg-gradient-to-br from-green-50 to-green-100 hover:shadow-md transition-shadow duration-200"
            >
              <Statistic
                title="Total de Apartamentos"
                value={120}
                prefix={<ApartmentOutlined className="text-green-500" />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              bordered={false}
              className="bg-gradient-to-br from-purple-50 to-purple-100 hover:shadow-md transition-shadow duration-200"
            >
              <Statistic
                title="Total de Inquilinos"
                value={89}
                prefix={<UserOutlined className="text-purple-500" />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              bordered={false}
              className="bg-gradient-to-br from-orange-50 to-orange-100 hover:shadow-md transition-shadow duration-200"
            >
              <Statistic
                title="Contratos Ativos"
                value={76}
                prefix={<FileTextOutlined className="text-orange-500" />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
        </Row>
      </div>

      {/* Content Section */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            title="Atividades Recentes" 
            bordered={false}
            className="h-full shadow-sm hover:shadow-md transition-shadow duration-200"
            headStyle={{ borderBottom: '1px solid #f0f0f0' }}
          >
            <div className="space-y-4">
              <div className="flex items-center p-3 bg-gray-50 rounded-lg">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    Novo contrato assinado - Apto 204
                  </p>
                  <p className="text-xs text-gray-500">há 2 horas</p>
                </div>
              </div>
              <div className="flex items-center p-3 bg-gray-50 rounded-lg">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    Manutenção agendada - Prédio B
                  </p>
                  <p className="text-xs text-gray-500">há 4 horas</p>
                </div>
              </div>
              <div className="flex items-center p-3 bg-gray-50 rounded-lg">
                <div className="w-2 h-2 bg-yellow-500 rounded-full mr-3"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    Pagamento em atraso - Apto 315
                  </p>
                  <p className="text-xs text-gray-500">há 1 dia</p>
                </div>
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            title="Quick Actions" 
            bordered={false}
            className="h-full shadow-sm hover:shadow-md transition-shadow duration-200"
            headStyle={{ borderBottom: '1px solid #f0f0f0' }}
          >
            <div className="grid grid-cols-2 gap-4">
              <button className="flex flex-col items-center p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors duration-200 border border-blue-200">
                <BuildOutlined className="text-2xl text-blue-500 mb-2" />
                <span className="text-sm font-medium text-blue-700">
                  Adicionar Prédio
                </span>
              </button>
              <button className="flex flex-col items-center p-4 bg-green-50 hover:bg-green-100 rounded-lg transition-colors duration-200 border border-green-200">
                <ApartmentOutlined className="text-2xl text-green-500 mb-2" />
                <span className="text-sm font-medium text-green-700">
                  Novo Apartamento
                </span>
              </button>
              <button className="flex flex-col items-center p-4 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors duration-200 border border-purple-200">
                <UserOutlined className="text-2xl text-purple-500 mb-2" />
                <span className="text-sm font-medium text-purple-700">
                  Cadastrar Inquilino
                </span>
              </button>
              <button className="flex flex-col items-center p-4 bg-orange-50 hover:bg-orange-100 rounded-lg transition-colors duration-200 border border-orange-200">
                <FileTextOutlined className="text-2xl text-orange-500 mb-2" />
                <span className="text-sm font-medium text-orange-700">
                  Novo Contrato
                </span>
              </button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
