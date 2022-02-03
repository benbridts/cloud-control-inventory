from dependency_utils import (
    ResourceDependency as Dependency,
    DynamicDependency,
    CheckEnabledDependency as CheckEnabled,
    list_wafv2_scopes,
    list_quicksight_accounts,
    is_audit_manager_enabled,
    is_cloudformation_publisher,
)

EXCLUDES = (
    # Error in the provider
    # https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-amplify/issues/14
    "AWS::Amplify::App",
    # https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-cloudformation/issues/82
    "AWS::CloudFormation::ModuleDefaultVersion",
    # https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-cloudformation/issues/82
    "AWS::CloudFormation::ResourceDefaultVersion",
    "AWS::CodeGuruReviewer::RepositoryAssociation",  # security token
    "AWS::GameLift::GameServerGroup",  # security token
    "AWS::KMS::Key",  # https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-kms/issues/40
    "AWS::Route53::DNSSEC",  # security token
    "AWS::Route53::KeySigningKey",  # security token
    "AWS::IoTCoreDeviceAdvisor::SuiteDefinition",  # security token
    "AWS::ServiceCatalogAppRegistry::Application",  # security token
    "AWS::ServiceCatalogAppRegistry::AttributeGroup",  # security token
    # Blocked by AWS::ApiGateway::RestApi not supporting List
    "AWS::ApiGateway::Authorizer",
    "AWS::ApiGateway::BasePathMapping",
    "AWS::ApiGateway::Deployment",
    "AWS::ApiGateway::DocumentationVersion",
    "AWS::ApiGateway::Model",
    "AWS::ApiGateway::RequestValidator",
    "AWS::ApiGateway::Resource",
    "AWS::ApiGateway::Stage",
    "AWS::ApiGateway::UsagePlanKey",
    # Blocked by AWS::AutoScaling::AutoScalingGroup not supporting List
    "AWS::AutoScaling::LifecycleHook",
    # Blocked by there not being an CloudControl Resource for Types
    "AWS::CloudFormation::ResourceVersion",
    # Blocked by AWS::CertificateManager::Certificate not supporting List
    "AWS::EC2::EnclaveCertificateIamRoleAssociation",
    # Blocked by AWS::ElasticLoadBalancingV2::LoadBalancer not supporting list
    "AWS::ElasticLoadBalancingV2::Listener",
    # Blocked by AWS::QLDB::Ledger not being supported in cloud control
    "AWS::QLDB::Stream",
    # other
    "AWS::Budgets::BudgetsAction",  # Maybe AccessDenied from linked accounts
    "AWS::CE::CostCategory",  # Maybe AccessDenied from linked accounts
    "AWS::ECS::TaskSet",  # requires Cluster, Service, Id instead of only Cluster, Service, like the CLI
    "AWS::EFS::MountTarget",  # fileSystemId or a mountTargetId
    "AWS::FMS::NotificationChannel",  # Account needs to be delegated by AWS FM
    "AWS::FMS::Policy",  # Account needs to be delegated by AWS FM
    "AWS::Glue::SchemaVersion",  # Needs inputs
    "AWS::ImageBuilder::Component",  # InternalFailure
    "AWS::IoTWireless::TaskDefinition",  # GeneralServiceException
    "AWS::Lex::ResourcePolicy",  # InternalFailure
    "AWS::LicenseManager::Grant",  # Access denied for operation 'List:License
    "AWS::LicenseManager::License",  # Access denied for operation 'List:License
    "AWS::Macie::CustomDataIdentifier",  # GeneralServiceException
    "AWS::Macie::FindingsFilter",  # Access denied for operation 'macie2::ListFindingsFilters
    "AWS::S3::MultiRegionAccessPointPolicy",  # InternalFailure,
    "AWS::S3Outposts::Bucket",  # Required property: [OutpostId]
    "AWS::SageMaker::ImageVersion",  # InternalFailure
    "AWS::ServiceCatalog::ServiceActionAssociation",  # InternalFailure
    "AWS::Signer::ProfilePermission",  # InternalFailure
    "AWS::SSMContacts::Contact",  # NotFound
    "AWS::SSMContacts::ContactChannel",  # NotFound
    "AWS::SSO::Assignment",  # Required property: [InstanceArn, PermissionSetArn, PrincipalId, PrincipalType, TargetId, TargetType]
    "AWS::SSO::InstanceAccessControlAttributeConfiguration",  # Required property: [InstanceArn] and not type for SSOInstance
    "AWS::SSO::PermissionSet",  # Required property: [InstanceArn, PermissionSetArn]
    "Cloudar::EC2::KeyPair",
)

EXCLUDES_GET = {
    "AWS::Athena::DataCatalog",  # ResourceNotFoundException - same problem with cli
    "AWS::EC2::PrefixList",  # InternalFailure on GetResource
    "AWS::ECS::CapacityProvider",  # InternalFailure on GetResource
    "AWS::ImageBuilder::Image",  # ResourceNotFoundException
    "AWS::Route53Resolver::ResolverRule",  # GeneralServiceException
    "AWS::CloudFormation::PublicTypeVersion",  # GeneralServiceException
}

DEPENDENCIES = {  # Our implementation only supports one parent_resource as dependency
    "AWS::Amplify::Branch": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::Amplify::Domain": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::AmplifyUIBuilder::Component": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::AmplifyUIBuilder::Theme": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::Athena::PreparedStatement": Dependency(parent="AWS::Athena::WorkGroup", mapping={"WorkGroup": "Name"}),
    "AWS::AuditManager::Assessment": CheckEnabled(function=is_audit_manager_enabled),
    "AWS::CloudFormation::Publisher": CheckEnabled(function=is_cloudformation_publisher),
    "AWS::EC2::TransitGatewayMulticastDomainAssociation": Dependency(
        parent="AWS::EC2::TransitGatewayMulticastDomain",
        mapping={"TransitGatewayMulticastDomainId": "TransitGatewayMulticastDomainId"},
    ),
    "AWS::EC2::TransitGatewayMulticastGroupMember": Dependency(
        parent="AWS::EC2::TransitGatewayMulticastDomain",
        mapping={"TransitGatewayMulticastDomainId": "TransitGatewayMulticastDomainId"},
    ),
    "AWS::EC2::TransitGatewayMulticastGroupSource": Dependency(
        parent="AWS::EC2::TransitGatewayMulticastDomain",
        mapping={"TransitGatewayMulticastDomainId": "TransitGatewayMulticastDomainId"},
    ),
    "AWS::ECS::TaskSet": Dependency(
        parent="AWS::ECS::Service", mapping={"Cluster": "Cluster", "Service": "ServiceName"}
    ),
    "AWS::EFS::MountTarget": Dependency(parent="AWS::EFS::FileSystem", mapping={"FileSystemId": "FileSystemId"}),
    "AWS::EKS::Addon": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    "AWS::EKS::FargateProfile": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    "AWS::ElasticLoadBalancingV2::ListenerRule": Dependency(
        parent="AWS::ElasticLoadBalancingV2::Listener", mapping={"ListenerArn": "ListenerArn"}
    ),
    "AWS::GlobalAccelerator::EndpointGroup": Dependency(
        parent="AWS::GlobalAccelerator::Listener", mapping={"ListenerArn": "ListenerArn"}
    ),
    "AWS::GlobalAccelerator::Listener": Dependency(
        parent="AWS::GlobalAccelerator::Accelerator", mapping={"AcceleratorArn": "AcceleratorArn"}
    ),
    "AWS::Glue::SchemaVersionMetadata": Dependency(
        parent="AWS::Glue::SchemaVersion", mapping={"SchemaVersionId": "VersionId"}
    ),
    "AWS::IoTSiteWise::AccessPolicy": Dependency(
        parent="AWS::IoTSiteWise::Project", mapping={"AccessPolicyResource.Project.Id": "ProjectId"}
    ),
    "AWS::IoTSiteWise::Dashboard": Dependency(parent="AWS::IoTSiteWise::Project", mapping={"ProjectId": "ProjectId"}),
    "AWS::IoTSiteWise::Project": Dependency(parent="AWS::IoTSiteWise::Portal", mapping={"PortalId": "PortalId"}),
    "AWS::Kendra::DataSource": Dependency(parent="AWS::Kendra::Index", mapping={"IndexId": "Id"}),
    "AWS::Kendra::Faq": Dependency(parent="AWS::Kendra::Index", mapping={"IndexId": "Id"}),
    "AWS::Lex::BotAlias": Dependency(parent="AWS::Lex::Bot", mapping={"BotId": "Id"}),
    "AWS::Lex::BotVersion": Dependency(parent="AWS::Lex::Bot", mapping={"BotId": "Id"}),
    "AWS::Lightsail::LoadBalancerTlsCertificate": Dependency(
        parent="AWS::Lightsail::LoadBalancerTlsCertificate", mapping={"LoadBalancerName": "LoadBalancerName"}
    ),
    "AWS::Location::TrackerConsumer": Dependency(
        parent="AWS::Location::Tracker", mapping={"TrackerName": "TrackerName"}
    ),
    "AWS::MediaConnect::FlowEntitlement": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowOutput": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowSource": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowVpcInterface": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaPackage::Asset": Dependency(
        parent="AWS::MediaPackage::PackagingGroup", mapping={"PackagingGroupId": "Id"}
    ),
    "AWS::MediaPackage::PackagingConfiguration": Dependency(
        parent="AWS::MediaPackage::PackagingGroup", mapping={"PackagingGroupId": "Id"}
    ),
    "AWS::NetworkFirewall::LoggingConfiguration": Dependency(
        parent="AWS::NetworkFirewall::Firewall", mapping={"FirewallArn": "FirewallArn"}
    ),
    "AWS::NetworkManager::CustomerGatewayAssociation": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::NetworkManager::Device": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::NetworkManager::Link": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::NetworkManager::LinkAssociation": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::NetworkManager::Site": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::NetworkManager::TransitGatewayRegistration": Dependency(
        parent="AWS::NetworkManager::GlobalNetwork", mapping={"GlobalNetworkId": "Id"}
    ),
    "AWS::QLDB::Stream": Dependency(parent="AWS::QLDB::Ledger", mapping={"LedgerName": "Name"}),
    "AWS::QuickSight::Analysis": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::Dashboard": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::DataSet": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::DataSource": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::Template": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::Theme": DynamicDependency(function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}),
    "AWS::RDS::DBProxyTargetGroup": Dependency(parent="AWS::RDS::DBProxy", mapping={"DBProxyName": "DBProxyName"}),
    "AWS::RefactorSpaces::Application": Dependency(
        parent="AWS::RefactorSpaces::Environment", mapping={"EnvironmentIdentifier": "EnvironmentIdentifier"}
    ),
    "AWS::RefactorSpaces::Route": Dependency(
        parent="AWS::RefactorSpaces::Application", mapping={"ApplicationIdentifier": "ApplicationIdentifier"}
    ),
    "AWS::RefactorSpaces::Service": Dependency(
        parent="AWS::RefactorSpaces::Application", mapping={"ApplicationIdentifier": "ApplicationIdentifier"}
    ),
    "AWS::S3Outposts::AccessPoint": Dependency(parent="AWS::S3Outposts::Bucket", mapping={"Bucket": "Arn"}),
    "AWS::WAFv2::IPSet": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::RegexPatternSet": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::RuleGroup": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::WebACL": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
}
