// Copyright (c) 2026, WSO2 LLC. (https://www.wso2.com).
//
// WSO2 LLC. licenses this file to you under the Apache License,
// Version 2.0 (the "License"); you may not use this file except
// in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

package services

import (
	"strings"

	"github.com/wso2/agent-manager/agent-manager-service/models"
)

// Discovery lists a binding's capabilities through its gateway, so the answer has been through the binding's own
// policies: mcp-acl-list drops what it hides, and mcp-rewrite renames entries to their client-facing names and, when
// it lists a kind, drops the entries it does not list. Stored as is, that answer would lose every hidden capability
// (Manage Tools could then never allow one again) and store client-facing names where backend names belong.
// mergeGatewayDiscovery undoes both from the policies AMS itself rendered.

const (
	mcpACLPolicyName     = "mcp-acl-list"
	mcpRewritePolicyName = "mcp-rewrite"
)

// mcpCapabilityKind is one list of a binding's capabilities: its section in the policies' params and the field that
// identifies an entry.
type mcpCapabilityKind struct {
	section, idKey string
}

var mcpCapabilityKinds = []mcpCapabilityKind{{"tools", "name"}, {"prompts", "name"}, {"resources", "uri"}}

// mergeGatewayDiscovery is what discovered, listed through the gateway, means for the binding cfg: each entry renamed
// back to its backend name, plus every stored entry the binding's policies hide from the gateway's answer, so a
// hidden capability is kept rather than lost. A capability added to the MCP server while hidden cannot be seen this
// way, and appears once a policy stops hiding it.
func mergeGatewayDiscovery(cfg models.MCPEndpointConfig, discovered *models.MCPProxyCapabilities) *models.MCPProxyCapabilities {
	acl, rewrite := mcpPolicyParams(cfg.Policies, mcpACLPolicyName), mcpPolicyParams(cfg.Policies, mcpRewritePolicyName)
	if acl == nil && rewrite == nil {
		return discovered
	}
	stored := cfg.Capabilities
	if stored == nil {
		stored = &models.MCPProxyCapabilities{}
	}
	if discovered == nil {
		discovered = &models.MCPProxyCapabilities{}
	}
	out := &models.MCPProxyCapabilities{
		Tools:     mergeKind(mcpCapabilityKinds[0], discovered.Tools, stored.Tools, acl, rewrite),
		Prompts:   mergeKind(mcpCapabilityKinds[1], discovered.Prompts, stored.Prompts, acl, rewrite),
		Resources: mergeKind(mcpCapabilityKinds[2], discovered.Resources, stored.Resources, acl, rewrite),
	}
	if out.Tools == nil && out.Prompts == nil && out.Resources == nil {
		return nil
	}
	return out
}

func mergeKind(
	kind mcpCapabilityKind, discovered, stored *[]map[string]interface{}, acl, rewrite map[string]interface{},
) *[]map[string]interface{} {
	backendOf, rewriteListed := rewriteNames(kind, rewrite)
	merged := make([]map[string]interface{}, 0)
	seen := map[string]bool{}
	if discovered != nil {
		for _, entry := range *discovered {
			id, _ := entry[kind.idKey].(string)
			if backend, ok := backendOf[id]; ok && backend != id {
				renamed := make(map[string]interface{}, len(entry))
				for k, v := range entry {
					renamed[k] = v
				}
				renamed[kind.idKey] = backend
				entry, id = renamed, backend
			}
			if id == "" || seen[id] {
				continue
			}
			seen[id] = true
			merged = append(merged, entry)
		}
	}
	if stored != nil {
		for _, entry := range *stored {
			id, _ := entry[kind.idKey].(string)
			if id == "" || seen[id] {
				continue
			}
			hiddenByRewrite := rewriteListed != nil && !rewriteListed[id]
			if hiddenByACL(kind, acl, id) || hiddenByRewrite {
				seen[id] = true
				merged = append(merged, entry)
			}
		}
	}
	if len(merged) == 0 {
		return nil
	}
	return &merged
}

// hiddenByACL reports a backend capability the binding's mcp-acl-list drops from list answers: in allow mode, an
// exception; in deny mode, anything that is not one. A kind with no ACL section, or no valid mode, hides nothing.
func hiddenByACL(kind mcpCapabilityKind, acl map[string]interface{}, id string) bool {
	section, _ := acl[kind.section].(map[string]interface{})
	if section == nil {
		return false
	}
	mode, _ := section["mode"].(string)
	isException := false
	if exceptions, ok := section["exceptions"].([]interface{}); ok {
		for _, e := range exceptions {
			if s, _ := e.(string); s == id {
				isException = true
				break
			}
		}
	}
	switch strings.ToLower(mode) {
	case "allow":
		return isException
	case "deny":
		return !isException
	default:
		return false
	}
}

// rewriteNames reads the binding's mcp-rewrite section for kind: each client-facing name's backend name (its target,
// or itself), and the set of backend names it lists. listed is nil when the policy does not list the kind, which
// then passes through unrenamed and unfiltered.
func rewriteNames(kind mcpCapabilityKind, rewrite map[string]interface{}) (backendOf map[string]string, listed map[string]bool) {
	entries, ok := rewrite[kind.section].([]interface{})
	if !ok {
		return nil, nil
	}
	backendOf, listed = map[string]string{}, map[string]bool{}
	for _, raw := range entries {
		entry, _ := raw.(map[string]interface{})
		client, _ := entry[kind.idKey].(string)
		client = strings.TrimSpace(client)
		if client == "" {
			continue
		}
		backend := client
		if target, _ := entry["target"].(string); strings.TrimSpace(target) != "" {
			backend = strings.TrimSpace(target)
		}
		backendOf[client], listed[backend] = backend, true
	}
	return backendOf, listed
}

// mcpPolicyParams is the params of the binding's policy named name; nil when it has none.
func mcpPolicyParams(policies []models.MCPPolicy, name string) map[string]interface{} {
	for _, p := range policies {
		if p.Name == name {
			if p.Params == nil {
				return map[string]interface{}{}
			}
			return p.Params
		}
	}
	return nil
}
