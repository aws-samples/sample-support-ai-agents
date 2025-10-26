import { Duration, Stack, StackProps, SymlinkFollowMode } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as path from "path";
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';

export class OptiraMetadataStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const supportDataBucketName = new cdk.CfnParameter(this, 'SupportDataBucket', {
      type: 'String',
      description: 'Name of the S3 bucket for support data'
    });

    const createNewBucket = new cdk.CfnParameter(this, 'CreateNewBucket', {
      type: 'String',
      default: 'true',
      allowedValues: ['true', 'false'],
      description: 'Create new S3 bucket (true) or use existing bucket (false)'
    });

    const packagingDirectory = path.join(__dirname, "../packaging");

    const zipDependencies = path.join(packagingDirectory, "dependencies.zip");
    const zipApp = path.join(packagingDirectory, "app.zip");

    // Create a lambda layer with dependencies to keep the code readable in the Lambda console
    const dependenciesLayer = new lambda.LayerVersion(this, "OptiraMetadataDependenciesLayer", {
      code: lambda.Code.fromAsset(zipDependencies),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      description: "Dependencies needed for OptiraMetadata lambda",
    });

    // Define the Lambda function with inline policies to avoid IAM dependency race conditions
    const OptiraMetadataFunction = new lambda.Function(this, "OptiraMetadataLambda", {
      runtime: lambda.Runtime.PYTHON_3_12,
      functionName: "OptiraMetadataFunction",
      description: "A function that create case metadata",
      handler: "lambda_function.lambda_handler",
      code: lambda.Code.fromAsset(zipApp),

      timeout: Duration.seconds(300),
      memorySize: 10240,
      layers: [dependenciesLayer],
      architecture: lambda.Architecture.ARM_64,
      role: new iam.Role(this, 'OptiraMetadataLambdaRole', {
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
        ],
        inlinePolicies: {
          S3AccessPolicy: new iam.PolicyDocument({
            statements: [
              new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['s3:ListBucket'],
                resources: [`arn:aws:s3:::${supportDataBucketName.valueAsString}`]
              }),
              new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                  's3:GetObject',
                  's3:PutObject',
                  's3:PutObjectAcl'
                ],
                resources: [`arn:aws:s3:::${supportDataBucketName.valueAsString}/*`]
              })
            ]
          }),
          BedrockKnowledgeBasePolicy: new iam.PolicyDocument({
            statements: [
              new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "bedrock:ListDataSources",
                    "bedrock:StartIngestionJob",
                    "bedrock:GetDataSource",
                    "bedrock:GetKnowledgeBase"
                ],
                "resources": [
                  "arn:aws:bedrock:*:*:knowledge-base/*",
                  "arn:aws:bedrock:*:*:data-source/*"
                ]
              })
            ]
          }),
          SecretsManagerPolicy: new iam.PolicyDocument({
            statements: [
              new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['secretsmanager:GetSecretValue'],
                resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:optira/*`]
              })
            ]
          })
        }
      })
    });

    OptiraMetadataFunction.addEnvironment("S3_BUCKET_NAME", supportDataBucketName.valueAsString)
    OptiraMetadataFunction.addEnvironment("S3_PREFIX", "support-cases")

  //[supportDataBucket.arnForObjects('*')]
       // Create scheduler role
    const schedulerRole = new iam.Role(this, 'SchedulerRole', {
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
      inlinePolicies: {
        SchedulerLambdaInvocationPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['lambda:InvokeFunction'],
              resources: [OptiraMetadataFunction.functionArn]
            })
          ]
        })
      }
    });

        // EventBridge rule for immediate execution after deployment
    const immediateExecutionRule = new events.Rule(this, 'ImmediateExecutionRule', {
      description: 'Triggers OptiraMetadataFunction immediately after stack creation',
      eventPattern: {
        source: ['aws.cloudformation'],
        detailType: ['CloudFormation Stack Status Change'],
        resources: [this.stackId],
        detail: {
          'stack-id': [this.stackId],
          'status-details': {
            status: ['CREATE_COMPLETE']
          }
        }
      }
    });

    immediateExecutionRule.addTarget(new targets.LambdaFunction(OptiraMetadataFunction, {
      event: events.RuleTargetInput.fromObject({
        bucket_name: supportDataBucketName.valueAsString
      })
    }));

    // EventBridge Scheduler for daily runs
    new scheduler.CfnSchedule(this, 'OptiraMetadataDailySchedule', {
      scheduleExpression: 'cron(0 7 ? * * *)',
      flexibleTimeWindow: {
        mode: 'OFF'
      },
      target: {
        arn: OptiraMetadataFunction.functionArn,
        input: JSON.stringify({
          past_no_of_days: 1,
          bucket_name: supportDataBucketName.valueAsString
        }),
        roleArn: schedulerRole.roleArn
      }
    });

    // EventBridge rule to trigger on S3 object creation
    const s3ObjectCreatedRule = new events.Rule(this, 'S3ObjectCreatedRule', {
      description: 'Rule to trigger metadata extraction when new support case files are uploaded',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [supportDataBucketName.valueAsString]
          },
          object: {
            key: [{
              prefix: 'support-cases/'
            }]
          }
        }
      }
    });

    s3ObjectCreatedRule.addTarget(new targets.LambdaFunction(OptiraMetadataFunction));
  }
}
