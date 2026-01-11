/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { IFireflyWorkbenchService, IFireflyThought } from '../common/firefly.js';
import { Disposable } from '../../../../base/common/lifecycle.js';
import { Emitter } from '../../../../base/common/event.js';
import { ILogService } from '../../../../platform/log/common/log.js';
import { registerSingleton, InstantiationType } from '../../../../platform/instantiation/common/extensions.js';
import { IMainProcessService } from '../../../../platform/ipc/common/mainProcessService.js';
import { FireflyChannelClient } from '../../../../platform/firefly/common/fireflyIpc.js';

export class FireflyWorkbenchService extends Disposable implements IFireflyWorkbenchService {

    readonly _serviceBrand: undefined;

    private readonly _onDidChangeThought = this._register(new Emitter<IFireflyThought>());
    readonly onDidChangeThought = this._onDidChangeThought.event;

    private readonly _onDidChangeStatus = this._register(new Emitter<void>());
    readonly onDidChangeStatus = this._onDidChangeStatus.event;

    private readonly _onDidChangeMode = this._register(new Emitter<boolean>());
    readonly onDidChangeMode = this._onDidChangeMode.event;

    private _isAutonomousMode: boolean = false;
    private _currentThought?: IFireflyThought;
    private _totalCost: number = 0;
    private _client: FireflyChannelClient;

    constructor(
        @ILogService private readonly logService: ILogService,
        @IMainProcessService private readonly mainProcessService: IMainProcessService
    ) {
        super();
        this.logService.info('[Firefly] Workbench Service Online.');

        this._client = new FireflyChannelClient(this.mainProcessService.getChannel('firefly'));

        this._register(this._client.onDidStatusChange(status => {
            if (status.currentThought && (!this._currentThought || status.currentThought !== this._currentThought.text)) {
                this._currentThought = { text: status.currentThought, type: 'reasoning' };
                this._onDidChangeThought.fire(this._currentThought);
            }

            if (status.totalCost !== undefined && status.totalCost !== this._totalCost) {
                this._totalCost = status.totalCost;
                this._onDidChangeStatus.fire();
            }

            if (status.isAutonomous !== undefined && status.isAutonomous !== this._isAutonomousMode) {
                this._isAutonomousMode = status.isAutonomous;
                this._onDidChangeMode.fire(this._isAutonomousMode);
            }
        }));

        this._client.getStatus().then(status => {
            this._totalCost = status.totalCost;
            this._isAutonomousMode = status.isAutonomous;
            if (status.currentThought) {
                this._currentThought = { text: status.currentThought, type: 'reasoning' };
            }
            this._onDidChangeStatus.fire();
            this._onDidChangeMode.fire(this._isAutonomousMode);
        });
    }

    isAutonomousMode(): boolean {
        return this._isAutonomousMode;
    }

    setAutonomousMode(enabled: boolean): void {
        if (this._isAutonomousMode !== enabled) {
            this._isAutonomousMode = enabled;
            this._onDidChangeMode.fire(enabled);
            this.logService.info(`[Firefly] Autonomous Mode: ${enabled ? 'ENABLED' : 'DISABLED'}`);
        }
    }

    getCurrentThought(): IFireflyThought | undefined {
        return this._currentThought;
    }

    getTotalCost(): number {
        return this._totalCost;
    }

    reportIntent(id: string, args: unknown[]): void {
        // Log user intent - later this will be sent to the Python backend via IPC
        this.logService.trace(`[Firefly] Observed User Intent: ${id}`, args);

        // Temporary: Simulate awareness
        this._currentThought = { text: `User invoked ${id}`, type: 'observation' };
        this._onDidChangeThought.fire(this._currentThought);
    }
}

registerSingleton(IFireflyWorkbenchService, FireflyWorkbenchService, InstantiationType.Delayed);
