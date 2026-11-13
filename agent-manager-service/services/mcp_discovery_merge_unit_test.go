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
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/wso2/agent-manager/agent-manager-service/models"
)

func capList(key string, ids ...string) *[]map[string]interface{} {
	out := make([]map[string]interface{}, 0, len(ids))
	for _, id := range ids {
		out = append(out, map[string]interface{}{key: id})
	}
	return &out
}

func idsOf(key string, list *[]map[string]interface{}) []string {
	if list == nil {
		return nil
	}
	out := []string{}
	for _, entry := range *list {
		out = append(out, entry[key].(string))
	}
	return out
}

func aclPolicy(section, mode string, exceptions ...string) models.MCPPolicy {
	ex := make([]interface{}, 0, len(exceptions))
	for _, e := range exceptions {
		ex = append(ex, e)
	}
	return models.MCPPolicy{Name: "mcp-acl-list", Version: "v1", Params: map[string]interface{}{
		section: map[string]interface{}{"mode": mode, "exceptions": ex},
	}}
}

// rewritePolicy maps each client-facing name to its backend target ("" for none) in section.
func rewritePolicy(section, key string, clientToTarget ...[2]string) models.MCPPolicy {
	entries := make([]interface{}, 0, len(clientToTarget))
	for _, pair := range clientToTarget {
		entry := map[string]interface{}{key: pair[0]}
		if pair[1] != "" {
			entry["target"] = pair[1]
		}
		entries = append(entries, entry)
	}
	return models.MCPPolicy{Name: "mcp-rewrite", Version: "v1", Params: map[string]interface{}{section: entries}}
}

// With neither policy, the gateway's answer is stored as it is.
func TestMergeGatewayDiscovery_NoPoliciesPassesThrough(t *testing.T) {
	discovered := &models.MCPProxyCapabilities{Tools: capList("name", "a")}
	cfg := models.MCPEndpointConfig{Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "a", "gone")}}

	assert.Same(t, discovered, mergeGatewayDiscovery(cfg, discovered))
}

// In deny mode the gateway lists only the exceptions: every other stored tool is kept, and a tool removed from the
// MCP server while allowed is dropped.
func TestMergeGatewayDiscovery_DenyModeKeepsDeniedStoredTools(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "read", "write", "removed")},
		Policies:     []models.MCPPolicy{aclPolicy("tools", "deny", "read", "removed")},
	}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{Tools: capList("name", "read")})

	require.NotNil(t, got)
	assert.Equal(t, []string{"read", "write"}, idsOf("name", got.Tools))
}

// In allow mode the gateway hides the exceptions: they are kept, and a newly added tool appears.
func TestMergeGatewayDiscovery_AllowModeKeepsExceptionsAndAddsNewTools(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "read", "delete", "dropped")},
		Policies:     []models.MCPPolicy{aclPolicy("tools", "allow", "delete")},
	}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{Tools: capList("name", "read", "brand_new")})

	require.NotNil(t, got)
	assert.Equal(t, []string{"read", "brand_new", "delete"}, idsOf("name", got.Tools))
}

// The gateway's answer carries rewrite's client-facing names: each is stored under its backend name again, and a
// stored tool the rewrite does not list (so the gateway drops) is kept.
func TestMergeGatewayDiscovery_RewriteNamesAreReversed(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "search_issues", "list_issues", "unlisted")},
		Policies: []models.MCPPolicy{rewritePolicy("tools", "name",
			[2]string{"find", "search_issues"}, [2]string{"list_issues", ""})},
	}
	discovered := []map[string]interface{}{{"name": "find", "description": "Find issues"}, {"name": "list_issues"}}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{Tools: &discovered})

	require.NotNil(t, got)
	assert.Equal(t, []string{"search_issues", "list_issues", "unlisted"}, idsOf("name", got.Tools))
	assert.Equal(t, "Find issues", (*got.Tools)[0]["description"], "the entry keeps the gateway's other fields")
	assert.Equal(t, "find", discovered[0]["name"], "the gateway's answer is not modified")
}

// ACL and rewrite together: a renamed tool comes back under its backend name, and what either hides is kept.
func TestMergeGatewayDiscovery_ACLAndRewriteTogether(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "search_issues", "delete_repo", "unlisted")},
		Policies: []models.MCPPolicy{
			aclPolicy("tools", "allow", "delete_repo"),
			rewritePolicy("tools", "name", [2]string{"find", "search_issues"}, [2]string{"delete_repo", ""}),
		},
	}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{Tools: capList("name", "find")})

	require.NotNil(t, got)
	assert.Equal(t, []string{"search_issues", "delete_repo", "unlisted"}, idsOf("name", got.Tools))
}

// Resources are identified by uri and prompts by name; a kind the policies do not cover passes through.
func TestMergeGatewayDiscovery_ResourcesAndPrompts(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{
			Resources: capList("uri", "repo://a", "repo://secret"),
			Prompts:   capList("name", "old_prompt"),
		},
		Policies: []models.MCPPolicy{aclPolicy("resources", "allow", "repo://secret")},
	}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{
		Resources: capList("uri", "repo://a"),
		Prompts:   capList("name", "new_prompt"),
	})

	require.NotNil(t, got)
	assert.Equal(t, []string{"repo://a", "repo://secret"}, idsOf("uri", got.Resources))
	assert.Equal(t, []string{"new_prompt"}, idsOf("name", got.Prompts), "prompts have no ACL section: as listed")
}

// A first discovery has nothing stored to keep; with everything hidden, nothing is stored.
func TestMergeGatewayDiscovery_NothingStoredNothingListed(t *testing.T) {
	cfg := models.MCPEndpointConfig{Policies: []models.MCPPolicy{aclPolicy("tools", "deny")}}

	assert.Nil(t, mergeGatewayDiscovery(cfg, nil))
}

// An ACL section with no valid mode hides nothing.
func TestMergeGatewayDiscovery_UnknownACLModeHidesNothing(t *testing.T) {
	cfg := models.MCPEndpointConfig{
		Capabilities: &models.MCPProxyCapabilities{Tools: capList("name", "a", "removed")},
		Policies:     []models.MCPPolicy{aclPolicy("tools", "sometimes", "removed")},
	}

	got := mergeGatewayDiscovery(cfg, &models.MCPProxyCapabilities{Tools: capList("name", "a")})

	require.NotNil(t, got)
	assert.Equal(t, []string{"a"}, idsOf("name", got.Tools))
}
