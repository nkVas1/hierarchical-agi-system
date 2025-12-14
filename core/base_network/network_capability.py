"""Network capability definitions and management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CapabilityType(Enum):
    """Types of capabilities a network can provide."""

    # Data Processing
    NLP_PROCESSING = "nlp_processing"
    VISION_PROCESSING = "vision_processing"
    AUDIO_PROCESSING = "audio_processing"
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"

    # Reasoning
    LOGICAL_REASONING = "logical_reasoning"
    CAUSAL_INFERENCE = "causal_inference"
    PATTERN_RECOGNITION = "pattern_recognition"
    ABSTRACT_REASONING = "abstract_reasoning"
    ANALOGICAL_REASONING = "analogical_reasoning"

    # Knowledge
    SEMANTIC_SEARCH = "semantic_search"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    CONCEPT_LINKING = "concept_linking"
    MEMORY_STORAGE = "memory_storage"
    FACT_VERIFICATION = "fact_verification"

    # Innovation
    IDEA_GENERATION = "idea_generation"
    HYPOTHESIS_FORMATION = "hypothesis_formation"
    CREATIVE_SYNTHESIS = "creative_synthesis"
    BRAINSTORMING = "brainstorming"
    NOVELTY_DETECTION = "novelty_detection"

    # Quality Control
    PERFORMANCE_MONITORING = "performance_monitoring"
    QUALITY_ASSESSMENT = "quality_assessment"
    ANOMALY_DETECTION = "anomaly_detection"
    EFFICIENCY_ANALYSIS = "efficiency_analysis"

    # Coordination
    QUERY_ROUTING = "query_routing"
    RESULT_AGGREGATION = "result_aggregation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    RESOURCE_ALLOCATION = "resource_allocation"

    # Communication
    NATURAL_LANGUAGE_UNDERSTANDING = "natural_language_understanding"
    EMOTIONAL_INTELLIGENCE = "emotional_intelligence"
    CONTEXT_MANAGEMENT = "context_management"
    DIALOGUE_MANAGEMENT = "dialogue_management"


@dataclass
class NetworkCapability:
    """Detailed capability specification for a network."""

    capability_type: CapabilityType
    name: str
    description: str
    version: str = "1.0.0"
    confidence_score: float = 1.0  # 0.0 to 1.0
    processing_time_ms: float = 0.0  # Average processing time
    accuracy_score: float = 1.0  # 0.0 to 1.0
    supported_inputs: Set[str] = field(default_factory=set)
    supported_outputs: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)  # Other required capabilities
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert capability to dictionary."""
        return {
            "capability_type": self.capability_type.value,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "accuracy_score": self.accuracy_score,
            "supported_inputs": list(self.supported_inputs),
            "supported_outputs": list(self.supported_outputs),
            "dependencies": list(self.dependencies),
            "metadata": self.metadata,
        }

    @property
    def quality_score(self) -> float:
        """Calculate overall quality score.

        Combines accuracy and confidence with efficiency considerations.
        """
        base_quality = (self.accuracy_score + self.confidence_score) / 2

        # Penalize slow processing (assuming 1000ms as baseline)
        efficiency_factor = min(1.0, 1000.0 / max(self.processing_time_ms, 1.0))

        return base_quality * 0.8 + efficiency_factor * 0.2


class CapabilityRegistry:
    """Registry for managing network capabilities."""

    def __init__(self):
        """Initialize capability registry."""
        self._capabilities: Dict[str, List[NetworkCapability]] = {}
        self._network_capabilities: Dict[str, Set[str]] = {}

    def register_capability(
        self, network_id: str, capability: NetworkCapability
    ) -> None:
        """Register a capability for a network.

        Args:
            network_id: ID of the network providing the capability
            capability: Capability specification
        """
        capability_key = capability.capability_type.value

        if capability_key not in self._capabilities:
            self._capabilities[capability_key] = []

        self._capabilities[capability_key].append(capability)

        if network_id not in self._network_capabilities:
            self._network_capabilities[network_id] = set()

        self._network_capabilities[network_id].add(capability_key)

    def unregister_network(self, network_id: str) -> None:
        """Unregister all capabilities for a network.

        Args:
            network_id: ID of the network to unregister
        """
        if network_id in self._network_capabilities:
            capabilities = self._network_capabilities.pop(network_id)

            # Remove from capability lists
            for cap_key in capabilities:
                if cap_key in self._capabilities:
                    self._capabilities[cap_key] = [
                        cap
                        for cap in self._capabilities[cap_key]
                        if cap.metadata.get("network_id") != network_id
                    ]

    def find_networks_by_capability(
        self, capability_type: CapabilityType, min_quality: float = 0.0
    ) -> List[NetworkCapability]:
        """Find networks that provide a specific capability.

        Args:
            capability_type: Type of capability to search for
            min_quality: Minimum quality score required

        Returns:
            List of matching capabilities sorted by quality
        """
        capability_key = capability_type.value
        capabilities = self._capabilities.get(capability_key, [])

        # Filter by quality and sort
        filtered = [
            cap for cap in capabilities if cap.quality_score >= min_quality
        ]
        filtered.sort(key=lambda x: x.quality_score, reverse=True)

        return filtered

    def get_network_capabilities(self, network_id: str) -> Set[str]:
        """Get all capabilities provided by a network.

        Args:
            network_id: ID of the network

        Returns:
            Set of capability type identifiers
        """
        return self._network_capabilities.get(network_id, set())

    def get_all_capability_types(self) -> List[str]:
        """Get all registered capability types.

        Returns:
            List of capability type identifiers
        """
        return list(self._capabilities.keys())
