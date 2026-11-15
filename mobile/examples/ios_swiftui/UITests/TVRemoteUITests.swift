/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import XCTest

/// Drives the Apple TV demo with the simulated Siri Remote.
final class TVRemoteUITests: XCTestCase {
  private let app = XCUIApplication()
  private let remote = XCUIRemote.shared

  override func setUpWithError() throws {
    continueAfterFailure = false
    app.launch()
  }

  /// Explore → Select (nothing selectable) → Play/Pause → Menu returns to the scene list
  /// without leaving the app.
  func testRemoteExploresAndMenuReturnsToScenes() throws {
    let explore = try waitForExploreEnabled()
    remote.press(.left)
    XCTAssertTrue(explore.hasFocus)
    remote.press(.select)

    let hint = app.staticTexts["exploreHint"]
    XCTAssertTrue(hint.waitForExistence(timeout: 5))
    XCTAssertFalse(explore.exists)

    // The opening preset (Espresso) has no `onSelect` behaviors.
    remote.press(.select)
    waitForStatus("Nothing selectable under the reticle")

    // Play/Pause resets the camera and stays in Explore.
    remote.press(.playPause)
    XCTAssertTrue(hint.exists)

    // Menu leaves Explore, but must not leave the app.
    remote.press(.menu)
    XCTAssertTrue(explore.waitForExistence(timeout: 5))
    XCTAssertFalse(hint.exists)
    XCTAssertEqual(app.state, .runningForeground)
  }

  /// Loads Workbench (XR-Live) and selects the knot under the reticle, which runs its
  /// `onSelect` behavior through `XRLiveRealityKitSession.handleTap(at:in:)`.
  func testRemoteSelectsNodeUnderReticle() throws {
    let explore = try waitForExploreEnabled()
    let workbench = app.buttons["preset-Workbench"]
    XCTAssertTrue(workbench.exists)
    move(.right, until: workbench)
    remote.press(.select)
    waitForStatus("Compiled", prefixOnly: true)

    move(.left, until: explore)
    remote.press(.select)
    XCTAssertTrue(app.staticTexts["exploreHint"].waitForExistence(timeout: 5))
    remote.press(.select)
    waitForStatus("Selected Torus_Knot_Artifact")
  }

  // MARK: Helpers

  /// Presses `direction` until `element` has focus, failing after one press per preset.
  private func move(_ direction: XCUIRemote.Button, until element: XCUIElement) {
    for _ in 0..<32 where !element.hasFocus {
      remote.press(direction)
    }
    XCTAssertTrue(element.hasFocus, "\(element) never received focus")
  }

  private func waitForExploreEnabled() throws -> XCUIElement {
    let explore = app.buttons["explore"]
    XCTAssertTrue(explore.waitForExistence(timeout: 30))
    let enabled = expectation(for: NSPredicate(format: "isEnabled == true"), evaluatedWith: explore)
    wait(for: [enabled], timeout: 60)
    return explore
  }

  private func waitForStatus(_ text: String, prefixOnly: Bool = false) {
    let status = app.staticTexts["status"]
    let predicate =
      prefixOnly
      ? NSPredicate(format: "label BEGINSWITH %@", text)
      : NSPredicate(format: "label == %@", text)
    let found = XCTWaiter.wait(
      for: [expectation(for: predicate, evaluatedWith: status)], timeout: 30)
    XCTAssertEqual(found, .completed, "status was \"\(status.label)\", expected \"\(text)\"")
  }
}
