#!/usr/bin/env node
import { App } from "aws-cdk-lib";
import { OptiraCollectorStack } from '../lib/optira-collector-stack';

const app = new App();
// prettier-ignore
new OptiraCollectorStack(app, "OptiraCollectorStack", {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.AWS_DEFAULT_REGION || process.env.CDK_DEFAULT_REGION 
  },
});

