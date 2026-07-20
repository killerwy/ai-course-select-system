import { homeForRole, LOGIN_PAGE } from './domain/navigation'
import { authService } from './services/runtime'

function relaunch(url: string): void {
  wx.reLaunch({ url })
}

App<IAppOption>({
  globalData: {},
  onLaunch() {
    void authService.restore()
      .then(session => relaunch(session ? homeForRole(session.user.role) : LOGIN_PAGE))
      .catch(() => relaunch(LOGIN_PAGE))
  },
})
