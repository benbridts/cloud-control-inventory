from dependency_utils import (
    ResourceDependency as Dependency,
    DynamicDependency,
    CheckEnabledDependency as CheckEnabled,
    StaticDependency,
    list_wafv2_scopes,
    list_quicksight_accounts,
    is_audit_manager_enabled,
    is_cloudformation_publisher,
)

EXCLUDES = (
    # Error in the provider
    # https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-cloudformation/issues/82
    "AWS::AppSync::DomainName",  # security token
    "AWS::Chatbot::MicrosoftTeamsChannelConfiguration",  # security token
    "AWS::CloudFormation::HookVersion",  # security token
    "AWS::CodeGuruReviewer::RepositoryAssociation",  # security token
    "AWS::Evidently::Segment",  # security token
    "AWS::MediaTailor::PlaybackConfiguration",  # security token
    "AWS::Pipes::Pipe",  # security token
    "AWS::RolesAnywhere::TrustAnchor",  # security token
    "AWS::Route53Resolver::FirewallDomainList",  # security token
    "AWS::Route53Resolver::FirewallRuleGroup",  # security token
    "AWS::Route53Resolver::FirewallRuleGroupAssociation",  # security token
    "AWS::SageMaker::DataQualityJobDefinition",  # security token
    "AWS::SageMaker::ModelBiasJobDefinition",  # security token
    "AWS::SageMaker::ModelExplainabilityJobDefinition",  # security token
    "AWS::SageMaker::ModelQualityJobDefinition",  # security token
    # Blocked by AWS::AutoScaling::AutoScalingGroup not supporting List
    "AWS::AutoScaling::LifecycleHook",
    # Blocked by there not being an CloudControl Resource for Types
    "AWS::CloudFormation::ResourceVersion",
    "AWS::CloudFormation::ResourceDefaultVersion",
    # Blocked by AWS::CertificateManager::Certificate not supporting List
    "AWS::EC2::EnclaveCertificateIamRoleAssociation",
    # Blocked by AWS::ElasticLoadBalancingV2::LoadBalancer not supporting list
    "AWS::ElasticLoadBalancingV2::Listener",
    # Blocked by AWS::QLDB::Ledger not being supported in cloud control
    "AWS::QLDB::Stream",
    # Blocked by AWS::Transfer::Server not supporting list
    "AWS::Transfer::Agreement",
    # other
    "AWS::ApiGatewayV2::Route",  # Property at /properties/RouteId is null
    "AWS::AppFlow::Connector",  # Connector with label S3 not found"
    "AWS::Budgets::BudgetsAction",  # Maybe AccessDenied from linked accounts
    "AWS::CE::CostCategory",  # Maybe AccessDenied from linked accounts
    "AWS::DevOpsGuru::ResourceCollection",  # Can throw failure because No CustomerResourceFilter present
    "AWS::EC2::CarrierGateway",  # not available in every region
    "AWS::ECS::TaskSet",  # requires Cluster, Service, Id instead of only Cluster, Service, like the CLI
    "AWS::EFS::MountTarget",  # fileSystemId or a mountTargetId
    "AWS::FMS::ResourceSet",  # Account needs to be delegated by AWS FM
    "AWS::FMS::NotificationChannel",  # Account needs to be delegated by AWS FM
    "AWS::FMS::Policy",  # Account needs to be delegated by AWS FM
    "AWS::Glue::SchemaVersion",  # Needs inputs
    "AWS::IdentityStore::Group",  # identityStoreId needed as input, no resource for that
    "AWS::IdentityStore::GroupMembership",  # identityStoreId needed as input, no resource for that
    "AWS::ImageBuilder::Component",  # InternalFailure
    "AWS::ImageBuilder::Image",  # InternalFailure
    "AWS::IoTWireless::TaskDefinition",  # GeneralServiceException
    "AWS::Lex::ResourcePolicy",  # InternalFailure
    "AWS::LicenseManager::Grant",  # Access denied for operation 'List:License
    "AWS::LicenseManager::License",  # Access denied for operation 'List:License
    "AWS::Macie::AllowList",  # InternalFailure
    "AWS::Macie::CustomDataIdentifier",  # Fails when not enabled in region
    "AWS::Macie::FindingsFilter",  # Fails when not enabled in region
    "AWS::Organizations::Account",  # AccessDeniedException when not management account
    "AWS::Organizations::OrganizationalUnit",  # AccessDeniedException when not management account
    "AWS::Organizations::Policy",  # not in management account
    "AWS::Organizations::ResourcePolicy",  # not in management account
    "AWS::RoboMaker::Fleet",  # support for the AWS RoboMaker application deployment feature has ended
    "AWS::RoboMaker::Robot",  # support for the AWS RoboMaker application deployment feature has ended
    "AWS::S3::MultiRegionAccessPointPolicy",  # InternalFailure,
    "AWS::S3Outposts::Bucket",  # Required property: [OutpostId]
    "AWS::Scheduler::ScheduleGroup",  # ResourceArn must not be null (but is not a property)
    "AWS::ServiceCatalog::ServiceActionAssociation",  # InternalFailure
    "AWS::SSMContacts::Contact",  # NotFound
    "AWS::SSMContacts::ContactChannel",  # NotFound
    "AWS::SSMContacts::Rotation",  # Account not found
    "AWS::SSO::Assignment",  # Required property: [InstanceArn, PermissionSetArn, PrincipalId, PrincipalType, TargetId, TargetType]
    "AWS::SSO::InstanceAccessControlAttributeConfiguration",  # Required property: [InstanceArn] and not type for SSOInstance
    "AWS::SSO::PermissionSet",  # Required property: [InstanceArn, PermissionSetArn]
    "AWS::XRay::Group",  # InternalFailure
)

EXCLUDES_GET = {
    "AWS::Athena::DataCatalog",  # ResourceNotFoundException - same problem with cli
    "AWS::CodePipeline::CustomActionType",  # ResourceNotFoundException on default resources
    "AWS::EC2::PrefixList",  # InternalFailure on GetResource
    "AWS::ECS::CapacityProvider",  # InternalFailure on GetResource
    "AWS::Route53Resolver::ResolverRule",  # InvalidRequestException - Cannot tag Auto Defined Rule.
    "AWS::CloudFormation::PublicTypeVersion",  # GeneralServiceException - Account is not registered as a publisher
    "AWS::RAM::Permission",  # Cannot deserialize in handler
    # There are a lot of these, and it is easy to run into downstream throttling.
    # We probably should improve the tool to do things more spread between resources.
    "AWS::SSM::Document",
}

DEPENDENCIES = {  # Our implementation only supports one parent_resource as dependency
    # Amplify
    "AWS::Amplify::Branch": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::Amplify::Domain": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::AmplifyUIBuilder::Component": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::AmplifyUIBuilder::Theme": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    "AWS::AmplifyUIBuilder::Form": Dependency(parent="AWS::Amplify::App", mapping={"AppId": "AppId"}),
    # ApiGateway
    "AWS::ApiGateway::Authorizer": Dependency(parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}),
    "AWS::ApiGateway::BasePathMapping": Dependency(
        parent="AWS::ApiGateway::DomainName", mapping={"DomainName": "DomainName"}
    ),
    "AWS::ApiGateway::Deployment": Dependency(parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}),
    "AWS::ApiGateway::DocumentationPart": Dependency(
        parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}
    ),
    "AWS::ApiGateway::DocumentationVersion": Dependency(
        parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}
    ),
    "AWS::ApiGateway::Model": Dependency(parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}),
    "AWS::ApiGateway::RequestValidator": Dependency(
        parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}
    ),
    "AWS::ApiGateway::Resource": Dependency(parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}),
    "AWS::ApiGateway::Stage": Dependency(parent="AWS::ApiGateway::RestApi", mapping={"RestApiId": "RestApiId"}),
    "AWS::ApiGateway::UsagePlanKey": Dependency(parent="AWS::ApiGateway::UsagePlan", mapping={"UsagePlanId": "Id"}),
    "AWS::ApiGatewayV2::Authorizer": Dependency(parent="AWS::ApiGatewayV2::Api", mapping={"ApiId": "ApiId"}),
    "AWS::ApiGatewayV2::Deployment": Dependency(parent="AWS::ApiGatewayV2::Api", mapping={"ApiId": "ApiId"}),
    "AWS::ApiGatewayV2::Model": Dependency(parent="AWS::ApiGatewayV2::Api", mapping={"ApiId": "ApiId"}),
    "AWS::ApiGatewayV2::Route": Dependency(parent="AWS::ApiGatewayV2::Api", mapping={"ApiId": "ApiId"}),
    # APS
    "AWS::APS::RuleGroupsNamespace": Dependency(parent="AWS::APS::Workspace", mapping={"Workspace": "WorkspaceId"}),
    # Athena
    "AWS::Athena::PreparedStatement": Dependency(parent="AWS::Athena::WorkGroup", mapping={"WorkGroup": "Name"}),
    # AuditManager
    "AWS::AuditManager::Assessment": CheckEnabled(function=is_audit_manager_enabled),
    # CloudFormation
    "AWS::CloudFormation::Publisher": CheckEnabled(function=is_cloudformation_publisher),
    "AWS::CloudFormation::HookDefaultVersion": Dependency(
        parent="AWS::CloudFormation::HookVersion", mapping={"TypeName": "TypeName"}
    ),
    "AWS::CloudFormation::HookTypeConfig": Dependency(
        parent="AWS::CloudFormation::HookVersion", mapping={"TypeName": "TypeName"}
    ),
    # DevOpsGuru
    "AWS::DevOpsGuru::ResourceCollection": StaticDependency(
        options=["AWS_CLOUD_FORMATION", "AWS_TAGS"], mapping_key="ResourceCollectionType"
    ),
    # EC2
    "AWS::EC2::IPAMAllocation": Dependency(parent="AWS::EC2::IPAMPool", mapping={"IpamPoolId": "IpamPoolId"}),
    "AWS::EC2::IPAMPoolCidr": Dependency(parent="AWS::EC2::IPAMPool", mapping={"IpamPoolId": "IpamPoolId"}),
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
    # ECS
    "AWS::ECS::TaskSet": Dependency(
        parent="AWS::ECS::Service", mapping={"Cluster": "Cluster", "Service": "ServiceName"}
    ),
    # EFS
    "AWS::EFS::MountTarget": Dependency(parent="AWS::EFS::FileSystem", mapping={"FileSystemId": "FileSystemId"}),
    # EKS
    "AWS::EKS::Addon": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    "AWS::EKS::FargateProfile": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    "AWS::EKS::IdentityProviderConfig": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    "AWS::EKS::Nodegroup": Dependency(parent="AWS::EKS::Cluster", mapping={"ClusterName": "Name"}),
    # ElasticLoadBalancing
    "AWS::ElasticLoadBalancingV2::ListenerRule": Dependency(
        parent="AWS::ElasticLoadBalancingV2::Listener", mapping={"ListenerArn": "ListenerArn"}
    ),
    # GlobalAccelerator
    "AWS::GlobalAccelerator::EndpointGroup": Dependency(
        parent="AWS::GlobalAccelerator::Listener", mapping={"ListenerArn": "ListenerArn"}
    ),
    "AWS::GlobalAccelerator::Listener": Dependency(
        parent="AWS::GlobalAccelerator::Accelerator", mapping={"AcceleratorArn": "AcceleratorArn"}
    ),
    # Glue
    "AWS::Glue::SchemaVersionMetadata": Dependency(
        parent="AWS::Glue::SchemaVersion", mapping={"SchemaVersionId": "VersionId"}
    ),
    # IotTwinMaker
    "AWS::IoTTwinMaker::ComponentType": Dependency(
        parent="AWS::IoTTwinMaker::Workspace", mapping={"WorkspaceId": "WorkspaceId"}
    ),
    "AWS::IoTTwinMaker::Entity": Dependency(
        parent="AWS::IoTTwinMaker::Workspace", mapping={"WorkspaceId": "WorkspaceId"}
    ),
    "AWS::IoTTwinMaker::Scene": Dependency(
        parent="AWS::IoTTwinMaker::Workspace", mapping={"WorkspaceId": "WorkspaceId"}
    ),
    "AWS::IoTTwinMaker::SyncJob": Dependency(
        parent="AWS::IoTTwinMaker::Workspace", mapping={"WorkspaceId": "WorkspaceId"}
    ),
    # IotSiteWise
    "AWS::IoTSiteWise::AccessPolicy": Dependency(
        parent="AWS::IoTSiteWise::Project", mapping={"AccessPolicyResource.Project.Id": "ProjectId"}
    ),
    "AWS::IoTSiteWise::Dashboard": Dependency(parent="AWS::IoTSiteWise::Project", mapping={"ProjectId": "ProjectId"}),
    "AWS::IoTSiteWise::Project": Dependency(parent="AWS::IoTSiteWise::Portal", mapping={"PortalId": "PortalId"}),
    # Kendra
    "AWS::Kendra::DataSource": Dependency(parent="AWS::Kendra::Index", mapping={"IndexId": "Id"}),
    "AWS::Kendra::Faq": Dependency(parent="AWS::Kendra::Index", mapping={"IndexId": "Id"}),
    # Lambda
    "AWS::Lambda::Url": Dependency(parent="AWS::Lambda::Function", mapping={"TargetFunctionArn": "Arn"}),
    # Lex
    "AWS::Lex::BotAlias": Dependency(parent="AWS::Lex::Bot", mapping={"BotId": "Id"}),
    "AWS::Lex::BotVersion": Dependency(parent="AWS::Lex::Bot", mapping={"BotId": "Id"}),
    # Lightsail
    "AWS::Lightsail::LoadBalancerTlsCertificate": Dependency(
        parent="AWS::Lightsail::LoadBalancerTlsCertificate",
        mapping={"LoadBalancerName": "LoadBalancerName"},
    ),
    # Location
    "AWS::Location::TrackerConsumer": Dependency(
        parent="AWS::Location::Tracker", mapping={"TrackerName": "TrackerName"}
    ),
    # Logs
    "AWS::Logs::LogStream": Dependency(parent="AWS::Logs::LogGroup", mapping={"LogGroupName": "LogGroupName"}),
    "AWS::Logs::SubscriptionFilter": Dependency(parent="AWS::Logs::LogGroup", mapping={"LogGroupName": "LogGroupName"}),
    # MediaConnect
    "AWS::MediaConnect::FlowEntitlement": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowOutput": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowSource": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    "AWS::MediaConnect::FlowVpcInterface": Dependency(parent="AWS::MediaConnect::Flow", mapping={"FlowArn": "FlowArn"}),
    # MediaPackage
    "AWS::MediaPackage::Asset": Dependency(
        parent="AWS::MediaPackage::PackagingGroup", mapping={"PackagingGroupId": "Id"}
    ),
    "AWS::MediaPackage::PackagingConfiguration": Dependency(
        parent="AWS::MediaPackage::PackagingGroup", mapping={"PackagingGroupId": "Id"}
    ),
    # MSK
    "AWS::MSK::BatchScramSecret": Dependency(parent="AWS::MSK::Cluster", mapping={"ClusterArn": "Arn"}),
    # NetworkFirewall
    "AWS::NetworkFirewall::LoggingConfiguration": Dependency(
        parent="AWS::NetworkFirewall::Firewall", mapping={"FirewallArn": "FirewallArn"}
    ),
    # NetworkManager
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
    # OpenSearch
    "AWS::OpenSearchServerless::AccessPolicy": StaticDependency(options=["data"], mapping_key="Type"),
    "AWS::OpenSearchServerless::SecurityConfig": StaticDependency(options=["saml"], mapping_key="Type"),
    "AWS::OpenSearchServerless::SecurityPolicy": StaticDependency(
        options=["encryption", "network"], mapping_key="Type"
    ),
    # QLDB
    "AWS::QLDB::Stream": Dependency(parent="AWS::QLDB::Ledger", mapping={"LedgerName": "Name"}),
    # QuickSight
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
    "AWS::QuickSight::RefreshSchedule": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::Template": DynamicDependency(
        function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}
    ),
    "AWS::QuickSight::Theme": DynamicDependency(function=list_quicksight_accounts, mapping={"AwsAccountId": "Account"}),
    # RDS
    "AWS::RDS::DBProxyTargetGroup": Dependency(parent="AWS::RDS::DBProxy", mapping={"DBProxyName": "DBProxyName"}),
    # RefactorSpaces
    "AWS::RefactorSpaces::Application": Dependency(
        parent="AWS::RefactorSpaces::Environment",
        mapping={"EnvironmentIdentifier": "EnvironmentIdentifier"},
    ),
    "AWS::RefactorSpaces::Route": Dependency(
        parent="AWS::RefactorSpaces::Application",
        mapping={"ApplicationIdentifier": "ApplicationIdentifier"},
    ),
    "AWS::RefactorSpaces::Service": Dependency(
        parent="AWS::RefactorSpaces::Application",
        mapping={"ApplicationIdentifier": "ApplicationIdentifier"},
    ),
    # S3Outpost
    "AWS::S3Outposts::AccessPoint": Dependency(parent="AWS::S3Outposts::Bucket", mapping={"Bucket": "Arn"}),
    # SageMaker
    "AWS::SageMaker::ImageVersion": Dependency(parent="AWS::SageMaker::Image", mapping={"ImageName": "ImageName"}),
    # Signer
    "AWS::Signer::ProfilePermission": Dependency(
        parent="AWS::Signer::SigningProfile", mapping={"ProfileName": "ProfileName"}
    ),
    # VPC Latice
    "AWS::VpcLattice::AccessLogSubscription": Dependency(
        parent="AWS::VpcLattice::Service", mapping={"ResourceIdentifier": "Id"}
    ),
    "AWS::VpcLattice::Listener": Dependency(parent="AWS::VpcLattice::Service", mapping={"ServiceIdentifier": "Id"}),
    "AWS::VpcLattice::Rule": Dependency(parent="AWS::VpcLattice::Listener", mapping={"listenerIdentifier": "Id"}),
    "AWS::VpcLattice::ServiceNetworkServiceAssociation": Dependency(
        parent="AWS::VpcLattice::Service", mapping={"ServiceIdentifier": "Id"}
    ),
    "AWS::VpcLattice::ServiceNetworkVpcAssociation": Dependency(
        parent="AWS::VpcLattice::ServiceNetwork", mapping={"ServiceNetworkIdentifier": "Id"}
    ),
    # WAF
    "AWS::WAFv2::IPSet": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::RegexPatternSet": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::RuleGroup": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
    "AWS::WAFv2::WebACL": DynamicDependency(function=list_wafv2_scopes, mapping={"Scope": "Scope"}),
}
