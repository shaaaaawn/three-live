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

import ThreeLiveCompiler
import UIKit
import UIKit.UIGestureRecognizerSubclass
import XCTest
import simd

@testable import ThreeLiveDemoTV

/// Siri Remote touch-surface swipes cannot be synthesized by `XCUIRemote` or the simulator, so
/// these tests feed `TVOrbitView.handlePan(_:)` a recognizer that reports a chosen translation.
@MainActor
final class TVOrbitViewTests: XCTestCase {
  /// A pan recognizer whose state and translation are set by the test. (UIKit ignores state
  /// changes on a recognizer that is not attached to a view, so `state` is stubbed too.)
  private final class StubPan: UIPanGestureRecognizer {
    var stubState: UIGestureRecognizer.State = .possible
    var stubTranslation = CGPoint.zero
    override var state: UIGestureRecognizer.State {
      get { stubState }
      set { stubState = newValue }
    }
    override func translation(in view: UIView?) -> CGPoint { stubTranslation }
  }

  private func swipe(_ view: TVOrbitView, by translation: CGPoint) {
    let pan = StubPan(target: nil, action: nil)
    pan.state = .began
    view.handlePan(pan)
    for step in 1...4 {
      pan.stubTranslation = CGPoint(
        x: translation.x * CGFloat(step) / 4, y: translation.y * CGFloat(step) / 4)
      pan.state = .changed
      view.handlePan(pan)
    }
    pan.state = .ended
    view.handlePan(pan)
  }

  /// Eases `orbit` to its targets and returns the settled eye position.
  private func settledEye(_ orbit: XROrbitCameraState) -> SIMD3<Double> {
    var orbit = orbit
    for _ in 0..<60 {
      _ = orbit.step(dt: 0.25, now: 0)
    }
    return orbit.eye
  }

  func testHorizontalSwipeOrbitsAroundTheTarget() {
    let view = TVOrbitView(frame: CGRect(x: 0, y: 0, width: 1920, height: 1080))
    let before = settledEye(view.orbit)
    swipe(view, by: CGPoint(x: 200, y: 0))
    let after = settledEye(view.orbit)

    XCTAssertGreaterThan(simd_distance(before, after), 0.1)
    XCTAssertEqual(after.y, before.y, accuracy: 1e-6, "A horizontal swipe keeps the elevation")
    XCTAssertEqual(
      simd_distance(after, view.orbit.target), simd_distance(before, view.orbit.target),
      accuracy: 1e-6, "Orbiting keeps the camera distance")
  }

  func testSwipingDownRaisesTheCamera() {
    let view = TVOrbitView(frame: CGRect(x: 0, y: 0, width: 1920, height: 1080))
    let before = settledEye(view.orbit)
    swipe(view, by: CGPoint(x: 0, y: 120))
    XCTAssertGreaterThan(settledEye(view.orbit).y, before.y)
  }
}
