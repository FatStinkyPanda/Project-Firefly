/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { createDecorator } from '../../../../platform/instantiation/common/instantiation.js';
import { Event } from '../../../../base/common/event.js';

export const IFireflyWorkbenchService = createDecorator<IFireflyWorkbenchService>('fireflyWorkbenchService');

export interface IFireflyThought {
    readonly text: string;
    readonly type: 'reasoning' | 'action' | 'observation' | 'user-chat';
}

export type SafetyMode = 'AUTO' | 'ORCHESTRATOR_ONLY' | 'MANUAL';

export interface IModelUsage {
    readonly modelId: string;
    readonly modelName: string;
    readonly tokens: number;
    readonly cost: number;
}

export interface IFireflyWorkbenchService {
    readonly _serviceBrand: undefined;

    readonly onDidChangeThought: Event<IFireflyThought>;
    readonly onDidChangeMode: Event<boolean>;
    readonly onDidChangeStatus: Event<void>;
    readonly onDidChangeSafetyMode: Event<SafetyMode>;
    readonly onDidChangeActiveModel: Event<string>;

    isAutonomousMode(): boolean;
    setAutonomousMode(enabled: boolean): void;

    getCurrentThought(): IFireflyThought | undefined;
    getTotalCost(): number;

    /**
     * Allows the workbench to report user intents directly to Firefly
     */
    reportIntent(id: string, args: unknown[]): void;

    // Chat
    sendChat(text: string): Promise<void>;

    // Agent Lifecycle
    createAgent(name: string, persona: string): Promise<string>;
    deleteAgent(id: string): Promise<void>;

    // Safety Mode Controls
    getSafetyMode(): SafetyMode;
    setSafetyMode(mode: SafetyMode): void;

    // Model Orchestration
    getActiveModel(): string;
    setActiveModel(modelId: string): void;
    getAvailableModels(): { id: string; name: string; provider: string }[];
    getModelUsage(): IModelUsage[];

    // Thought Stream
    getThoughtHistory(): IFireflyThought[];
}

