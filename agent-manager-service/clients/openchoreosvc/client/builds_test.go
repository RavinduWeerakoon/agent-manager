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

	"github.com/wso2/agent-manager/agent-manager-service/utils"
)

// covers the UpdateComponentBuildParameters write path
func TestBuildEndpointsFromInputInterface_MaxStreamingDurationSeconds(t *testing.T) {
	agentType := AgentTypeConfig{Type: string(utils.AgentTypeAPI), SubType: string(utils.AgentSubTypeCustomAPI)}

	t.Run("set value is included in the rebuilt endpoint map", func(t *testing.T) {
		inputInterface := &InputInterfaceConfig{
			Type:                        "HTTP",
			Port:                        8080,
			BasePath:                    "/",
			MaxStreamingDurationSeconds: int32Ptr(120),
		}

		endpoints, err := buildEndpointsFromInputInterface("agent-1", inputInterface, agentType)

		require.NoError(t, err)
		require.Len(t, endpoints, 1)
		assert.Equal(t, int32(120), endpoints[0]["maxStreamingDurationSeconds"])
	})

	t.Run("unset (nil) omits the key entirely", func(t *testing.T) {
		inputInterface := &InputInterfaceConfig{
			Type:     "HTTP",
			Port:     8080,
			BasePath: "/",
		}

		endpoints, err := buildEndpointsFromInputInterface("agent-1", inputInterface, agentType)

		require.NoError(t, err)
		require.Len(t, endpoints, 1)
		_, present := endpoints[0]["maxStreamingDurationSeconds"]
		assert.False(t, present, "expected no maxStreamingDurationSeconds key when the field is unset")
	})
}
