//
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

package client

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/wso2/agent-manager/agent-manager-service/clients/openchoreosvc/gen"
	"github.com/wso2/agent-manager/agent-manager-service/utils"
)

// int32Ptr returns a pointer to the given int32, for building *int32 fields
// (e.g. InputInterfaceConfig.MaxStreamingDurationSeconds) inline in tests.
func int32Ptr(v int32) *int32 {
	return &v
}

// TestBuildEndpoints_MaxStreamingDurationSeconds covers the write side of the
// MaxStreamingDurationSeconds round-trip: buildEndpoints must add the
// "maxStreamingDurationSeconds" key to the endpoint map only when the field is
// non-nil, mirroring how schemaFilePath/schemaType are conditionally handled,
// so old/default agents don't get a spurious 0 written into their workflow
// parameters.
func TestBuildEndpoints_MaxStreamingDurationSeconds(t *testing.T) {
	t.Run("set value is included in the endpoint map", func(t *testing.T) {
		req := CreateComponentRequest{
			Name:      "agent-1",
			AgentType: AgentTypeConfig{Type: string(utils.AgentTypeAPI), SubType: string(utils.AgentSubTypeCustomAPI)},
			InputInterface: &InputInterfaceConfig{
				Type:                        "HTTP",
				Port:                        8080,
				BasePath:                    "/",
				MaxStreamingDurationSeconds: int32Ptr(45),
			},
		}

		endpoints, err := buildEndpoints(req)

		require.NoError(t, err)
		require.Len(t, endpoints, 1)
		assert.Equal(t, int32(45), endpoints[0]["maxStreamingDurationSeconds"])
	})

	t.Run("unset (nil) omits the key entirely", func(t *testing.T) {
		req := CreateComponentRequest{
			Name:      "agent-1",
			AgentType: AgentTypeConfig{Type: string(utils.AgentTypeAPI), SubType: string(utils.AgentSubTypeCustomAPI)},
			InputInterface: &InputInterfaceConfig{
				Type:     "HTTP",
				Port:     8080,
				BasePath: "/",
			},
		}

		endpoints, err := buildEndpoints(req)

		require.NoError(t, err)
		require.Len(t, endpoints, 1)
		_, present := endpoints[0]["maxStreamingDurationSeconds"]
		assert.False(t, present, "expected no maxStreamingDurationSeconds key when the field is unset")
	})
}

// TestExtractInputInterface_MaxStreamingDurationSeconds covers the read side:
// extractInputInterface must parse "maxStreamingDurationSeconds" back out of
// the endpoints array parsed from the component's workflow parameters (JSON
// numbers decode as float64 in a map[string]interface{}, matching how
// "port" is already handled), and must leave the field nil when the key is
// absent (e.g. agents created before this fix, or without the field set).
func TestExtractInputInterface_MaxStreamingDurationSeconds(t *testing.T) {
	t.Run("present key is parsed into a non-nil pointer", func(t *testing.T) {
		params := map[string]interface{}{
			"endpoints": []interface{}{
				map[string]interface{}{
					"name":                        "agent-1-endpoint",
					"port":                        float64(8080),
					"type":                        "HTTP",
					"basePath":                    "/",
					"maxStreamingDurationSeconds": float64(45),
				},
			},
		}

		got := extractInputInterface(params)

		require.NotNil(t, got)
		require.NotNil(t, got.MaxStreamingDurationSeconds)
		assert.Equal(t, int32(45), *got.MaxStreamingDurationSeconds)
	})

	t.Run("absent key leaves the field nil", func(t *testing.T) {
		params := map[string]interface{}{
			"endpoints": []interface{}{
				map[string]interface{}{
					"name":     "agent-1-endpoint",
					"port":     float64(8080),
					"type":     "HTTP",
					"basePath": "/",
				},
			},
		}

		got := extractInputInterface(params)

		require.NotNil(t, got)
		assert.Nil(t, got.MaxStreamingDurationSeconds)
	})
}

// TestConvertComponentFromTyped_MaxStreamingDurationSeconds exercises the full
// read-side round-trip from a gen.Component (as returned by GetComponent) down
// to models.AgentResponse.InputInterface.MaxStreamingDurationSeconds, covering
// both branches of the field-by-field merge in convertComponentFromTyped:
//   - when comp.Spec.Parameters has no "basePath", agent.InputInterface starts
//     nil and is assigned wholesale from extractInputInterface's result.
//   - when comp.Spec.Parameters DOES have a top-level "basePath" (as some
//     agents do), agent.InputInterface is pre-populated before the workflow
//     parameters are merged in field-by-field; MaxStreamingDurationSeconds
//     must be included in that merge exactly like Port/Type/Schema/BasePath/
//     Visibility already are, or a redeploy of such an agent would silently
//     drop a persisted value even though extractInputInterface computed it.
func TestConvertComponentFromTyped_MaxStreamingDurationSeconds(t *testing.T) {
	newComponent := func(specParameters *map[string]interface{}) *gen.Component {
		workflowParams := map[string]interface{}{
			"endpoints": []interface{}{
				map[string]interface{}{
					"name":                        "agent-1-endpoint",
					"port":                        float64(8080),
					"type":                        "HTTP",
					"basePath":                    "/",
					"maxStreamingDurationSeconds": float64(45),
					"visibility":                  []interface{}{"Public"},
				},
			},
		}
		return &gen.Component{
			Metadata: gen.ObjectMeta{Name: "agent-1"},
			Spec: &gen.ComponentSpec{
				ComponentType: struct {
					Kind *gen.ComponentSpecComponentTypeKind `json:"kind,omitempty"`
					Name string                              `json:"name"`
				}{Name: "internal-agent/agent-api"},
				Owner: struct {
					ProjectName string `json:"projectName"`
				}{ProjectName: "proj"},
				Parameters: specParameters,
				Workflow: &gen.ComponentWorkflowConfig{
					Name:       "build-workflow",
					Parameters: &workflowParams,
				},
			},
		}
	}

	t.Run("InputInterface starts nil: assigned wholesale from extractInputInterface", func(t *testing.T) {
		comp := newComponent(nil)

		agent, err := convertComponentFromTyped(comp)

		require.NoError(t, err)
		require.NotNil(t, agent.InputInterface)
		require.NotNil(t, agent.InputInterface.MaxStreamingDurationSeconds)
		assert.Equal(t, int32(45), *agent.InputInterface.MaxStreamingDurationSeconds)
	})

	t.Run("InputInterface pre-populated from spec.Parameters basePath: field-by-field merge still carries it through", func(t *testing.T) {
		specParams := map[string]interface{}{"basePath": "/"}
		comp := newComponent(&specParams)

		agent, err := convertComponentFromTyped(comp)

		require.NoError(t, err)
		require.NotNil(t, agent.InputInterface)
		require.NotNil(t, agent.InputInterface.MaxStreamingDurationSeconds)
		assert.Equal(t, int32(45), *agent.InputInterface.MaxStreamingDurationSeconds)
	})

	t.Run("absent from workflow endpoint: nil, not zero", func(t *testing.T) {
		workflowParams := map[string]interface{}{
			"endpoints": []interface{}{
				map[string]interface{}{
					"name":     "agent-1-endpoint",
					"port":     float64(8080),
					"type":     "HTTP",
					"basePath": "/",
				},
			},
		}
		comp := &gen.Component{
			Metadata: gen.ObjectMeta{Name: "agent-1"},
			Spec: &gen.ComponentSpec{
				ComponentType: struct {
					Kind *gen.ComponentSpecComponentTypeKind `json:"kind,omitempty"`
					Name string                              `json:"name"`
				}{Name: "internal-agent/agent-api"},
				Owner: struct {
					ProjectName string `json:"projectName"`
				}{ProjectName: "proj"},
				Workflow: &gen.ComponentWorkflowConfig{
					Name:       "build-workflow",
					Parameters: &workflowParams,
				},
			},
		}

		agent, err := convertComponentFromTyped(comp)

		require.NoError(t, err)
		require.NotNil(t, agent.InputInterface)
		assert.Nil(t, agent.InputInterface.MaxStreamingDurationSeconds)
	})
}
