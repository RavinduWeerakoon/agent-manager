import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Get Started',
      collapsed: false,
      items: [
        'get-started/what-is-amp',
        'get-started/architecture',
        'get-started/quick-start',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      collapsed: false,
      items: [
        'concepts/organization',
        'concepts/project',
        'concepts/environment',
        'concepts/gateway',
        'concepts/deployment-pipeline',
        'concepts/agent-lifecycle',
        'concepts/internal-and-external-agent',
        'concepts/agentid',
        'concepts/agent-kind-and-catalog',
        'concepts/agent-sandboxing',
        'concepts/evaluation',
        'concepts/observability',
        'concepts/llm-service-provider',
        'concepts/agent-tools'
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      collapsed: false,
      items: [
        {
          type: 'category',
          label: 'Installation',
          collapsed: false,
          items: [
            'guides/on-k3d',
            'guides/on-your-environment',
            'guides/on-a-vm',
            'guides/cli-installation',
          ],
        },
        {
          type: 'category',
          label: 'Evaluation & Observability',
          collapsed: false,
          items: [
            'guides/custom-evaluators',
            'guides/evaluation-monitors',
          ],
        },
        {
          type: 'category',
          label: 'Securing Agent Endpoints',
          collapsed: false,
          items: [
            'guides/configure-identity-providers',
            {
              type: 'category',
              label: 'Configure Sandboxing',
              collapsed: true,
              items: [
                'guides/isolation-tiers/gvisor',
                'guides/isolation-tiers/kata',
              ],
            },
            'guides/secure-agent-endpoints-with-api-keys',
            'guides/secure-agent-endpoints-with-oauth',
            'guides/configure-cors-for-agent-endpoints',
          ],
        },
        {
          type: 'category',
          label: 'Platform Administration',
          collapsed: false,
          items: [
            'guides/register-ai-gateway',
            'guides/register-llm-service-provider',
            'guides/register-mcp-proxy',
            'guides/environment-management',
            'guides/instrumentation-catalog',
            'guides/amp-instrumentation',
          ],
        },
        {
          type: 'category',
          label: 'Agent Identity and Access Management',
          collapsed: false,
          items: [
            'guides/authorize-agent-access-to-mcp-tools',
            'guides/use-agentid-in-platform-hosted-agents',
            'guides/retrieve-agentid-for-externally-hosted-agents',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
      collapsed: false,
      items: [
        'tutorials/create-your-first-agent',
        'tutorials/observe-first-agent',
        'tutorials/controlling-what-agents-can-access',
        'tutorials/roll-out-agent-version',
      ],
    },
    {
      type: 'category',
      label: 'References',
      collapsed: false,
      items: [
        'reference/rest-api-reference',
        {
          type: 'category',
          label: 'CLI',
          collapsed: true,
          items: [
            'reference/cli/overview',
            'reference/cli/login',
            'reference/cli/context',
            'reference/cli/project',
            'reference/cli/agent',
            'reference/cli/llm-provider',
            'reference/cli/skills',
            'reference/cli/version',
            'reference/cli/api',
          ],
        },
        'reference/mcp-server',
        'reference/observer-mcp-server',
        'reference/helm-charts',
        'reference/authorization',
      ],
    },
    {
      type: 'category',
      label: 'Contributing',
      collapsed: false,
      items: [
        'contributing/contributing',
      ],
    },
  ],
};

export default sidebars;
