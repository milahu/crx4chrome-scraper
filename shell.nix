{
  pkgs ? import <nixpkgs> {}
}:

let
  extraPythonPackages = rec {
    cdp-socket = pkgs.python3.pkgs.callPackage ./nix/cdp-socket.nix {};
    # error: Package ‘python3.10-selenium-driverless-1.6.3.3’ has an unfree license (‘cc-by-nc-sa-40’), refusing to evaluate.
    selenium-driverless = pkgs.python3.pkgs.callPackage ./nix/selenium-driverless.nix {
      inherit cdp-socket;
      #cdp-socket = pkgs.python3.pkgs.callPackage ./nix/cdp-socket.nix {};
      #selenium = pkgs.python3.pkgs.callPackage ./nix/selenium.nix { };
    };
    aiohttp-chromium = pkgs.python3.pkgs.callPackage ./nix/aiohttp-chromium.nix {
      inherit selenium-driverless;
    };
    # fix: ModuleNotFoundError: No module named 'selenium.webdriver.common.devtools'
    # https://github.com/milahu/nixpkgs/issues/20
    #selenium = pkgs.python3.pkgs.callPackage ./nix/selenium.nix { };
  };

  python = pkgs.python3.withPackages (pythonPackages:
  (with pythonPackages; [
    aiohttp
    /*
    aiohttp-socks # https://stackoverflow.com/a/76656557/10440128
    aiodns # make aiohttp faster
    brotli # make aiohttp faster
    psutil
    beautifulsoup4 # html parser
    */
  ])
  ++
  (with extraPythonPackages; [
    /*
    selenium-driverless
    cdp-socket
    */
    #selenium
    aiohttp-chromium
  ])
  );

in

pkgs.mkShell rec {

  buildInputs = (with pkgs; [
    #
  ]) ++ [
    python
  ]
  ++
  (with extraPythonPackages; [
    /*
    selenium-driverless
    cdp-socket
    */
    aiohttp-chromium
  ]);

}
