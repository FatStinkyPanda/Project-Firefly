/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { localize, localize2 } from '../../../../nls.js';
import { Registry } from '../../../../platform/registry/common/platform.js';
import { Extensions as ViewExtensions, IViewContainersRegistry, ViewContainerLocation, IViewsRegistry } from '../../../common/views.js';
import { SyncDescriptor } from '../../../../platform/instantiation/common/descriptors.js';
import { ViewPaneContainer } from '../../../browser/parts/views/viewPaneContainer.js';
import { FireflyViewPane } from './fireflyViewPane.js';
import { Codicon } from '../../../../base/common/codicons.js';
import { registerIcon } from '../../../../platform/theme/common/iconRegistry.js';

// Define Firefly Icon (using a sparkled/intelligence icon for now)
const fireflyIcon = registerIcon('firefly-agent', Codicon.sparkle, localize('fireflyAgentIcon', 'Icon for the Firefly Agent Hub.'));

// 1. Register View Container
const containerId = 'workbench.view.firefly';
const container = Registry.as<IViewContainersRegistry>(ViewExtensions.ViewContainersRegistry).registerViewContainer({
    id: containerId,
    title: localize2('fireflyAgentHub', "Agent Hub"),
    icon: fireflyIcon,
    ctorDescriptor: new SyncDescriptor(ViewPaneContainer, [containerId, { mergeViewWithContainerWhenSingleView: true }]),
    storageId: containerId,
    hideIfEmpty: true,
    order: 100,
}, ViewContainerLocation.Sidebar);

// 2. Register View Pane
const viewId = 'workbench.view.firefly.pane';
Registry.as<IViewsRegistry>(ViewExtensions.ViewsRegistry).registerViews([{
    id: viewId,
    name: localize2('fireflyAgentStatus', "Agent Status"),
    containerIcon: fireflyIcon,
    ctorDescriptor: new SyncDescriptor(FireflyViewPane),
    canMoveView: true,
    canToggleVisibility: false,
    collapsed: false,
    order: 1,
}], container);
